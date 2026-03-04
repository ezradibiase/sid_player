#!/usr/bin/env python3
"""
Script COMPLETO per risolvere problemi IGDB
"""

import requests
import os
import json

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=" * 60)
    print("IGDB TOKEN FIXER per SIDPlayer C64")
    print("=" * 60)
    print()

def get_credentials():
    """Ottiene le credenziali dall'utente"""
    print("🔑 PRIMA: Ottieni Client ID e Client Secret da:")
    print("   https://dev.twitch.tv/console/apps")
    print()
    
    client_id = input("Inserisci il Client ID: ").strip()
    client_secret = input("Inserisci il Client Secret: ").strip()
    
    return client_id, client_secret

def get_access_token(client_id, client_secret):
    """Ottiene un nuovo Access Token"""
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    
    print("\n🔄 Richiesta del token in corso...")
    response = requests.post(url, params=params)
    
    if response.status_code != 200:
        print(f"❌ Errore {response.status_code}: {response.text}")
        return None
    
    data = response.json()
    
    if 'access_token' not in data:
        print(f"❌ Risposta inattesa: {data}")
        return None
    
    return data['access_token'], data['expires_in']

def save_credentials(client_id, access_token):
    """Salva le credenziali nel file"""
    with open('igdb_credentials.txt', 'w') as f:
        f.write(f"{client_id}\n{access_token}")
    
    print("💾 File salvato come 'igdb_credentials.txt'")
    
    # Mostra anteprima file
    print("\n📄 Contenuto del file:")
    print("-" * 30)
    with open('igdb_credentials.txt', 'r') as f:
        for i, line in enumerate(f, 1):
            print(f"Riga {i}: {line.strip()}")
    print("-" * 30)

def test_credentials(client_id, access_token):
    """Testa se le credenziali funzionano"""
    print("\n🧪 Test delle credenziali...")
    
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    # Query semplice per test
    test_query = 'fields name; where id = 1942; limit 1;'
    
    try:
        response = requests.post(
            'https://api.igdb.com/v4/games',
            headers=headers,
            data=test_query,
            timeout=10
        )
        
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESSO! Credenziali valide!")
            print(f"📊 Risposta: {data}")
            return True
        elif response.status_code == 401:
            print("❌ ERRORE 401: Access Token non valido")
            print("   Controlla di aver usato l'Access Token, non il Client Secret")
            return False
        else:
            print(f"⚠️  Errore {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Errore nel test: {e}")
        return False

def show_current_file():
    """Mostra il contenuto attuale del file"""
    if os.path.exists('igdb_credentials.txt'):
        print("\n📄 File corrente 'igdb_credentials.txt':")
        print("-" * 30)
        with open('igdb_credentials.txt', 'r') as f:
            content = f.read()
            if not content.strip():
                print("(file vuoto)")
            else:
                lines = content.strip().split('\n')
                for i, line in enumerate(lines, 1):
                    print(f"Riga {i}: {line[:30]}...")
        print("-" * 30)
        
        # Analizza i tipi
        if len(lines) >= 2:
            client_id = lines[0].strip()
            token = lines[1].strip()
            
            print("\n🔍 Analisi:")
            print(f"Client ID: {len(client_id)} caratteri")
            print(f"Token: {len(token)} caratteri")
            
            # Indizi su cosa potrebbe essere
            if token.startswith('Bearer '):
                print("⚠️  Token inizia con 'Bearer ' - RIMUOVI 'Bearer '!")
            if len(token) < 20:
                print("⚠️  Token troppo corto - probabilmente non è un Access Token")
            if ' ' in token:
                print("⚠️  Token contiene spazi - non dovrebbe!")
    else:
        print("\n📄 File 'igdb_credentials.txt' non esiste")

def main():
    print_header()
    
    # Mostra il file corrente
    show_current_file()
    
    print("\n" + "=" * 60)
    print("INIZIAMO LA PROCEDURA DI FIX")
    print("=" * 60)
    
    # Ottieni nuove credenziali
    client_id, client_secret = get_credentials()
    
    if not client_id or not client_secret:
        print("\n❌ Client ID o Client Secret mancanti!")
        return
    
    # Ottieni Access Token
    result = get_access_token(client_id, client_secret)
    if not result:
        return
    
    access_token, expires_in = result
    
    print(f"\n✅ Token ottenuto con successo!")
    print(f"   Token: {access_token[:30]}...")
    print(f"   Scade tra: {expires_in} secondi ({expires_in//86400} giorni)")
    
    # Testa le credenziali
    if test_credentials(client_id, access_token):
        # Salva se funziona
        save = input("\n💾 Salvare le nuove credenziali? (s/n): ")
        if save.lower() == 's':
            save_credentials(client_id, access_token)
            
            # Verifica finale
            verify = input("\n🔍 Verificare di nuovo il file salvato? (s/n): ")
            if verify.lower() == 's':
                show_current_file()
                
            print("\n🎉 Procedura completata!")
            print("\nOra puoi avviare SIDPlayer con:")
            print("1. python sid_play.py")
            print("2. Clicca LOAD")
            print("3. Clicca PLAY")
            print("\nSe ancora non funziona, riavvia questo script.")
    else:
        print("\n❌ Le credenziali non funzionano. Riprova.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Operazione annullata")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
    finally:
        input("\nPremi Invio per uscire...")