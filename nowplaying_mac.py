"""
nowplaying_mac.py — Integrazione macOS Now Playing per SIDPlayer C64.

Usa MPNowPlayingInfoCenter e MPRemoteCommandCenter (framework MediaPlayer)
tramite PyObjC per far apparire il player nei controlli multimediali di sistema:
Control Center, Touch Bar, tasti F-media, Siri.

Richiede: macOS + pyobjc-core (già incluso con macOS).
Su Linux/Windows il modulo viene importato ma non fa nulla (HAS_NOWPLAYING=False).

NOTE TECNICHE — Thread safety e GIL
-------------------------------------
MPRemoteCommandCenter consegna i comandi su thread ObjC arbitrari.

PROBLEMA: chiamare qualsiasi API Tkinter (incluso master.after()) da un thread
non-main è VIETATO in Tkinter. Internamente, _tkinter.so usa la variabile globale
`tcl_tstate` per salvare/ripristinare il thread state del main thread. Se un thread
in background esegue master.after() → ENTER_TCL → sovrascrive tcl_tstate con il
proprio tstate → il main thread chiama LEAVE_TCL → PyEval_RestoreThread(wrong_tstate)
→ SIGABRT ("PyEval_RestoreThread: NULL tstate").

SOLUZIONE: handleEvent_ mette il comando in una queue.Queue (operazione pura Python,
nessuna API Tkinter). Il main thread drena la coda via after() ogni 100ms.
Queue.put() usa Py_BEGIN_ALLOW_THREADS al livello C, che salva/ripristina il tstate
nel frame locale senza toccare tcl_tstate di Tkinter → sicuro.

SECONDA SOLUZIONE: ivar ObjC di tipo NSInteger (non id), così ObjC non esegue
mai retain/release su oggetti Python → nessun rischio di dealloc cross-thread
che corrompe il reference-counting Python.
"""

import sys
import queue as _queue

HAS_NOWPLAYING = False
_ns = {}   # namespace del bundle MediaPlayer

if sys.platform == "darwin":
    try:
        import objc
        from Foundation import NSObject
        objc.loadBundle(
            'MediaPlayer',
            bundle_path='/System/Library/Frameworks/MediaPlayer.framework',
            module_globals=_ns,
        )
        HAS_NOWPLAYING = True
    except Exception:
        pass

# ------------------------------------------------------------------
# Chiavi MPNowPlayingInfo (valori costanti del framework Apple)
# ------------------------------------------------------------------
_KEY_TITLE    = "title"
_KEY_ARTIST   = "artist"
_KEY_DURATION = "playbackDuration"
_KEY_RATE     = "MPNowPlayingInfoPropertyPlaybackRate"
_KEY_ELAPSED  = "MPNowPlayingInfoPropertyElapsedPlaybackTime"

# MPNowPlayingPlaybackState: 0=Unknown 1=Playing 2=Paused 3=Stopped
_STATE_PLAYING = 1
_STATE_PAUSED  = 2
_STATE_STOPPED = 3

# ------------------------------------------------------------------
# Coda thread-safe per i comandi remoti
# Produttori: thread ObjC (via handleEvent_)
# Consumatori: main thread Tkinter (via _drain_commands polling)
# ------------------------------------------------------------------
_cmd_queue: _queue.Queue = _queue.Queue()

# Registro dei callback: key (int) → callable Python
# Accesso solo da main thread (put durante init, get durante drain).
_CALLBACKS: dict = {}
_next_key: list  = [0]   # lista mutabile: evita 'nonlocal' in closure

def _register(cb):
    _next_key[0] += 1
    k = _next_key[0]
    _CALLBACKS[k] = cb
    return k

def _unregister(k):
    _CALLBACKS.pop(k, None)


# ------------------------------------------------------------------
# NSObject adapter GIL-safe.
# Ivar di tipo NSInteger (q): ObjC gestisce solo un numero intero,
# mai un puntatore Python → nessun retain/release cross-thread.
# ------------------------------------------------------------------
if HAS_NOWPLAYING:
    class _CommandTarget(NSObject):
        """
        Adapter per MPRemoteCommand.
        handleEvent_ è chiamato da thread ObjC: mette solo un intero nella coda
        → nessuna API Tkinter, nessun oggetto Python toccato da ObjC.
        """
        _key = objc.ivar(type=b'q')   # NSInteger

        @objc.python_method
        def initWithKey_(self, key):
            self = objc.super(_CommandTarget, self).init()
            if self is None:
                return None
            self._key = key
            return self

        @objc.typedSelector(b'q@:@')   # NSInteger handleEvent:(id)event
        def handleEvent_(self, event):
            # UNICA operazione: put nella queue Python — thread-safe, zero Tkinter.
            _cmd_queue.put(self._key)
            return 0   # MPRemoteCommandHandlerStatusSuccess


# ------------------------------------------------------------------
# Classe pubblica
# ------------------------------------------------------------------
class NowPlayingManager:
    """
    Gestisce l'integrazione Now Playing con macOS.

    Parametri
    ----------
    master    : widget Tkinter root
    on_play   : callable — avvia o riprende
    on_pause  : callable — mette in pausa
    on_next   : callable — traccia successiva
    on_prev   : callable — traccia precedente
    on_stop   : callable — stop
    """

    _POLL_MS = 100   # ms tra un drain e il successivo

    def __init__(self, master, on_play, on_pause, on_next, on_prev, on_stop):
        self._master   = master
        self._info     = None
        self._targets  = []     # (MPRemoteCommand, _CommandTarget, key)
        self._active   = False
        self._poll_job = None

        if not HAS_NOWPLAYING:
            return

        try:
            self._info = _ns['MPNowPlayingInfoCenter'].defaultCenter()
            cc         = _ns['MPRemoteCommandCenter'].sharedCommandCenter()

            # Disabilita comandi non gestiti
            for attr in (
                'changePlaybackRateCommand', 'seekBackwardCommand',
                'seekForwardCommand', 'skipBackwardCommand', 'skipForwardCommand',
                'changeRepeatModeCommand', 'changeShuffleModeCommand',
                'ratingCommand', 'likeCommand', 'dislikeCommand', 'bookmarkCommand',
            ):
                try:
                    getattr(cc, attr)().setEnabled_(False)
                except Exception:
                    pass

            # Registra i comandi gestiti.
            # I callback vengono sempre eseguiti sul main thread (via _drain_commands).
            pairs = [
                (cc.playCommand(),            on_play),
                (cc.pauseCommand(),           on_pause),
                (cc.togglePlayPauseCommand(), on_play),
                (cc.nextTrackCommand(),       on_next),
                (cc.previousTrackCommand(),   on_prev),
                (cc.stopCommand(),            on_stop),
            ]
            for cmd, cb in pairs:
                cmd.setEnabled_(True)
                key = _register(cb)
                t   = _CommandTarget.alloc().initWithKey_(key)
                cmd.addTarget_action_(t, b'handleEvent:')
                self._targets.append((cmd, t, key))

            self._active = True

            # Avvia il polling della coda sul main thread
            self._poll_job = master.after(self._POLL_MS, self._drain_commands)

        except Exception:
            import traceback
            traceback.print_exc()
            self._info   = None
            self._active = False

    def _drain_commands(self):
        """
        Eseguito sul main thread ogni _POLL_MS ms.
        Drena la coda dei comandi remoti e chiama i callback in sicurezza.
        """
        while not _cmd_queue.empty():
            try:
                key = _cmd_queue.get_nowait()
                cb  = _CALLBACKS.get(key)
                if cb:
                    cb()
            except _queue.Empty:
                break
            except Exception:
                pass
        # Ri-schedula (finché attivo)
        if self._active:
            self._poll_job = self._master.after(self._POLL_MS, self._drain_commands)

    # ------------------------------------------------------------------

    def update(self, title="", artist="", duration=None, elapsed=0.0, is_playing=True):
        """Aggiorna i metadati Now Playing visibili nel Control Center."""
        if not self._info:
            return
        try:
            info = {
                _KEY_TITLE:   title  or "Unknown",
                _KEY_ARTIST:  artist or "",
                _KEY_RATE:    1.0 if is_playing else 0.0,
                _KEY_ELAPSED: float(elapsed),
            }
            if duration and duration > 0:
                info[_KEY_DURATION] = float(duration)
            self._info.setNowPlayingInfo_(info)
            self._info.setPlaybackState_(_STATE_PLAYING if is_playing else _STATE_PAUSED)
        except Exception:
            pass

    def set_playing(self):
        if not self._info:
            return
        try:
            existing = self._info.nowPlayingInfo()
            info = dict(existing) if existing else {}
            info[_KEY_RATE] = 1.0
            self._info.setNowPlayingInfo_(info)
            self._info.setPlaybackState_(_STATE_PLAYING)
        except Exception:
            pass

    def set_paused(self):
        if not self._info:
            return
        try:
            existing = self._info.nowPlayingInfo()
            info = dict(existing) if existing else {}
            info[_KEY_RATE] = 0.0
            self._info.setNowPlayingInfo_(info)
            self._info.setPlaybackState_(_STATE_PAUSED)
        except Exception:
            pass

    def clear(self):
        if not self._info:
            return
        try:
            self._info.setNowPlayingInfo_(None)
            self._info.setPlaybackState_(_STATE_STOPPED)
        except Exception:
            pass

    def deactivate(self):
        """Rimuove tutti i target e ferma il polling (chiamare su quit)."""
        self._active = False
        if self._poll_job:
            try:
                self._master.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        try:
            for cmd, target, key in self._targets:
                cmd.removeTarget_(target)
                _unregister(key)
        except Exception:
            pass
        self._targets.clear()
        self.clear()
