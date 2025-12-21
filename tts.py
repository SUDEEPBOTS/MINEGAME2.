import requests
import os
from database import get_all_voice_keys, remove_voice_key, get_custom_voice

def generate_voice(text):
    keys = get_all_voice_keys()
    voice_id = get_custom_voice()
    
    # Debugging Print: Check karo keys aayi ya nahi
    print(f"🔍 Debug: Database se {len(keys)} keys mili. Voice ID: {voice_id}")

    if not keys:
        print("❌ No Voice Keys Found in DB!")
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    CHUNK_SIZE = 1024

    for api_key in keys:
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.8,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        try:
            print(f"🎤 Trying Key: {api_key[:5]}... on ID: {voice_id}")
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                file_path = f"mimi_voice_{os.urandom(3).hex()}.mp3"
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk: f.write(chunk)
                return file_path
            
            # 🔥 CHANGE: Abhi delete mat karo, bas print karo
            elif response.status_code in [401, 402]:
                print(f"🚫 Key Dead/Quota Full: {api_key[:5]}... (Not Deleting for Debug)")
                # remove_voice_key(api_key)  <-- Is line ko comment kar diya
                continue
            
            else:
                print(f"⚠️ TTS Error ({response.status_code}): {response.text}")
                continue

        except Exception as e:
            print(f"❌ TTS Exception: {e}")
            continue
            
    return None
