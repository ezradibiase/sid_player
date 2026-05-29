"""
nowplaying_mac.py — Integrazione macOS Now Playing per SIDPlayer C64.

Usa MPNowPlayingInfoCenter e MPRemoteCommandCenter (framework MediaPlayer)
tramite PyObjC per far apparire il player nei controlli multimediali di sistema:
Control Center, Touch Bar, tasti F-media, Siri.

Richiede: macOS + pyobjc-core (già incluso con macOS).
Su Linux/Windows il modulo viene importato ma non fa nulla (HAS_NOWPLAYING=False).
"""

import sys

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
# Classe adapter NSObject per target-action di MPRemoteCommand
# ------------------------------------------------------------------
if HAS_NOWPLAYING:
    class _CommandTarget(NSObject):
        """
        Adapter che collega un MPRemoteCommand a un callable Python.
        Deve restituire MPRemoteCommandHandlerStatus (NSInteger, 0=Success).
        """
        _callback = objc.ivar()

        @objc.python_method
        def initWithCallback(self, callback):
            self = objc.super(_CommandTarget, self).init()
            if self is None:
                return None
            self._callback = callback
            return self

        @objc.typedSelector(b'q@:@')   # NSInteger handleEvent:(id)event
        def handleEvent_(self, event):
            if self._callback:
                self._callback()
            return 0   # MPRemoteCommandHandlerStatusSuccess


# ------------------------------------------------------------------
# Classe pubblica
# ------------------------------------------------------------------
class NowPlayingManager:
    """
    Gestisce l'integrazione Now Playing con macOS.

    Parametri
    ----------
    master    : widget Tkinter root — usato per .after() (thread-safe verso UI)
    on_play   : callable — avvia o riprende
    on_pause  : callable — mette in pausa
    on_next   : callable — traccia successiva
    on_prev   : callable — traccia precedente
    on_stop   : callable — stop
    """

    def __init__(self, master, on_play, on_pause, on_next, on_prev, on_stop):
        self._master   = master
        self._info     = None   # MPNowPlayingInfoCenter
        self._targets  = []     # list of (MPRemoteCommand, _CommandTarget)
        self._active   = False

        if not HAS_NOWPLAYING:
            return

        try:
            self._info = _ns['MPNowPlayingInfoCenter'].defaultCenter()
            cc         = _ns['MPRemoteCommandCenter'].sharedCommandCenter()

            # Disabilita comandi non gestiti (altrimenti il sistema li mostra grayed-out)
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

            # Comandi gestiti → callback via after() per thread-safety con Tkinter
            def _mk(cb):
                def _wrap():
                    master.after(0, cb)
                return _wrap

            pairs = [
                (cc.playCommand(),            _mk(on_play)),
                (cc.pauseCommand(),           _mk(on_pause)),
                (cc.togglePlayPauseCommand(), _mk(on_play)),   # toggle → gioca sicuro con play
                (cc.nextTrackCommand(),       _mk(on_next)),
                (cc.previousTrackCommand(),   _mk(on_prev)),
                (cc.stopCommand(),            _mk(on_stop)),
            ]
            for cmd, cb in pairs:
                cmd.setEnabled_(True)
                t = _CommandTarget.alloc().initWithCallback(cb)
                cmd.addTarget_action_(t, b'handleEvent:')
                self._targets.append((cmd, t))

            self._active = True

        except Exception as exc:
            # Non bloccare l'avvio dell'app se qualcosa va storto
            import traceback
            traceback.print_exc()
            self._info   = None
            self._active = False

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
        """Aggiorna solo lo stato di riproduzione → playing."""
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
        """Aggiorna solo lo stato di riproduzione → paused."""
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
        """Rimuove le info Now Playing (chiamare su stop)."""
        if not self._info:
            return
        try:
            self._info.setNowPlayingInfo_(None)
            self._info.setPlaybackState_(_STATE_STOPPED)
        except Exception:
            pass

    def deactivate(self):
        """Rimuove tutti i target dai comandi remoti (chiamare su quit)."""
        if not self._active:
            return
        try:
            for cmd, target in self._targets:
                cmd.removeTarget_(target)
        except Exception:
            pass
        self._targets.clear()
        self.clear()
        self._active = False
