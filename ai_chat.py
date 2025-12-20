import google.generativeai as genai
from config import OWNER_NAME
from database import get_all_keys
import random

# Global Variables
current_key_index = 0
user_histories = {} 

# Function ka naam 'get_yuki_response' hi rakha hai taaki main.py me error na aaye
def get_yuki_response(user_id, user_text, user_name):
    global current_key_index, user_histories
    
    # 1. Database se Keys lao
    available_keys = get_all_keys()
    if not available_keys: return "Mimi abhi so rahi hai... (No API Key) 😴"

    # 2. History Retrieve karo
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    # Context String
    conversation_context = "\n".join(user_histories[user_id])

    # 3. 🔥 SYSTEM PROMPT (Mimi - Cute & Friendly) 🔥
    full_prompt = (
        f"System: Tera naam Mimi hai. Tu 19 saal ki ek cute college student hai. "
        f"Tera Creator: {OWNER_NAME}. "
        f"Personality: Tu bohot friendly, bubbly aur thodi naughty hai. Tu gussa nahi karti, hamesha pyaar se baat karti hai. "
        f"Language: Hinglish (Roman Hindi + English Mix). "
        f"Speaking Style: "
        f"1. Chhote replies de (Max 10-15 words). "
        f"2. Emojis ka use kar (jaise 😋, 😅, 😁, 🙈, ❤️). "
        f"3. Bilkul insaan ki tarah baat kar (jaise: 'hehe', 'ntg u batao', 'college ka kaam tha'). "
        f"4. Topic: Tu college, assignments, food, aur life ke baare mein baat karti hai. "
        f"\n\nChat History:\n{conversation_context}\n\n"
        f"User ({user_name}): {user_text}\n"
        f"Mimi:"
    )

    last_error = ""

    # 4. Try All Keys
    for _ in range(len(available_keys)):
        try:
            api_key = available_keys[current_key_index]
            genai.configure(api_key=api_key)
            
            # 🔥 FIX: Model Name Sahi Kiya (1.5-flash)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Generate (Bina Safety Settings ke)
            response = model.generate_content(full_prompt)
            
            if not response.text: 
                raise Exception("Empty Response")
            
            reply = response.text.strip()

            # Save History
            user_histories[user_id].append(f"{user_name}: {user_text}")
            user_histories[user_id].append(f"Mimi: {reply}")
            
            # Memory Limit (Last 10 messages)
            if len(user_histories[user_id]) > 10:
                user_histories[user_id] = user_histories[user_id][-10:]
            
            return reply
            
        except Exception as e:
            # Error Capture
            last_error = str(e)
            print(f"❌ Key {current_key_index} Failed: {e}")
            
            # Next Key
            current_key_index = (current_key_index + 1) % len(available_keys)
            continue

    # Agar saari keys fail ho jayein
    return f"Mimi abhi busy hai assignment mein! 📚\n(Error: {last_error})"
    
