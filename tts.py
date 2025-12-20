import requests
import os
from database import get_all_voice_keys, remove_voice_key, get_custom_voice

def generate_voice(text):
    """
    Auto-Switching Logic with Custom Voice Support:
    1. Database se current Voice ID aur saari API Keys uthayega.
    2. Ek-ek karke keys try karega.
    3. Agar key dead (401/402) mili to use DB se uda dega aur agli try karega.
    """
    
    # 1. DB se settings aur keys lo
    keys = get_all_voice_keys()
    voice_id = get_custom_voice() # Admin panel se set ki gayi ID
    
    if not keys:
        print("❌ No Voice Keys Found in DB!")
        return None

    # ElevenLabs API URL
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    CHUNK_SIZE = 1024

    for api_key in keys:
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        # Voice Settings: Multilingual v2 Hindi ke liye best hai
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.45,       # Thoda emotions ke liye
                "similarity_boost": 0.8, # Asli awaaz jaisa lagne ke liye
                "style": 0.0,            # Normal rakha hai
                "use_speaker_boost": True
            }
        }

        try:
            print(f"🎤 Trying Voice Key: {api_key[:8]}*** | Voice: {voice_id}")
            response = requests.post(url, json=data, headers=headers)
            
            # ✅ SUCCESS: Voice Note ban gaya
            if response.status_code == 200:
                # Unique filename taki files takraye nahi
                file_path = f"mimi_voice_{os.urandom(3).hex()}.mp3"
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                return file_path
            
            # ⚠️ QUOTA EXHAUSTED / DEAD KEY (Error 401/402)
            elif response.status_code in [401, 402]:
                print(f"🚫 Key Dead/Quota Full: {api_key[:8]}***. Removing from DB...")
                remove_voice_key(api_key) # Database se dead key delete
                continue # Agli key par jao
            
            else:
                print(f"⚠️ TTS Error ({response.status_code}): {response.text}")
                continue

        except Exception as e:
            print(f"❌ TTS Exception: {e}")
            continue
            
    print("❌ All available voice keys failed.")
    return None
