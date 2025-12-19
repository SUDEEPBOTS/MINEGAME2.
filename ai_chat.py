import google.generativeai as genai
from config import OWNER_NAME
from database import get_all_keys
import random

# Global Variables
current_key_index = 0
user_histories = {}  # 🧠 MEMORY STORE

def get_yuki_response(user_id, user_text, user_name):
    global current_key_index, user_histories
    
    # 1. Database se Keys lao
    available_keys = get_all_keys()
    if not available_keys: return "Bhai pehle /addkey se API Key toh add kar!"

    # 2. History Retrieve karo
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # History context string banao
    conversation_context = "\n".join(user_histories[user_id])

    # 3. System Prompt
    system_instruction = (
        f"Tera naam Yuki hai. Tu 17 saal ki Delhi wali ladki hai. "
        f"Tu Class 12th mein hai. "
        f"Mood: Thoda Moody (Kabhi gussa, kabhi emotional, kabhi chill). "
        f"Creator: Tera owner {OWNER_NAME} hai. (Naam tabhi lena jab pucha jaye). "
        f"Language: Hinglish, Delhi slang (yaar, whh, scene, op). "
        f"Short Reply Rule: Sirf 1 line (Max 10-30 words). "
        f"Memory: Pichli baaton ko yaad rakh kar reply karna. "
        f"\n[CHAT HISTORY START]\n{conversation_context}\n[CHAT HISTORY END]\n"
    )

    # 4. Loop through keys until success
    # Hum loop utni baar chalayenge jitni keys hain
    for _ in range(len(available_keys)):
        try:
            # Current Key nikalo
            api_key = available_keys[current_key_index]
            genai.configure(api_key=api_key)
            
            # 🔥 FIX: Model Name Sahi Kiya (1.5-flash)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Request generate karo
            response = model.generate_content(
                f"{system_instruction}\nUser ({user_name}): {user_text}\nYuki:"
            )
            
            if not response.text: 
                raise Exception("Empty Response from AI")
            
            reply = response.text.strip()

            # 5. History Update (Success hone par hi save karo)
            user_histories[user_id].append(f"{user_name}: {user_text}")
            user_histories[user_id].append(f"Yuki: {reply}")
            
            # Sirf last 6 messages rakho memory save karne ke liye
            if len(user_histories[user_id]) > 6:
                user_histories[user_id] = user_histories[user_id][-6:]
            
            return reply
            
        except Exception as e:
            print(f"⚠️ Key Failed (Key Index: {current_key_index}): {e}")
            
            # Agar error aaya toh Next Key par switch karo
            current_key_index = (current_key_index + 1) % len(available_keys)
            continue

    return "Server busy hai yaar, thodi der baad aana! 😵‍💫"
    
