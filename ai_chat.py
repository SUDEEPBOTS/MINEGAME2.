import google.generativeai as genai
from config import OWNER_NAME
from database import get_all_keys
import random

# Global Index to track rotation
current_key_index = 0

def get_next_key(keys_list):
    """Next API Key nikalta hai list se"""
    global current_key_index
    if not keys_list: return None
    current_key_index = (current_key_index + 1) % len(keys_list)
    return keys_list[current_key_index]

def get_yuki_response(user_text, user_name):
    global current_key_index
    
    # 1. Database se Keys lao
    available_keys = get_all_keys()
    
    if not available_keys:
        return "Arre boss ne abhi tak API Key nahi daali! (No Keys in DB)"

    # SYSTEM PROMPT (Yuki Persona - Updated)
    system_instruction = (
        f"Tera naam Yuki hai. Tu 17 saal ki Delhi wali ladki hai. "
        f"Tu abhi Class 12th me padhti hai (Board exams ka stress hai thoda). "
        f"Hobbies: Tujhe Gaming ka pagalpan hai (Free Fire, PUBG/BGMI, COD). "
        f"Tera owner {OWNER_NAME} hai, wo tera creator hai. "
        f"User ka naam {user_name} hai. "
        f"Reply style: Hinglish, Delhi slang (yaar, bhai, scene, op), thoda Gamer attitude. "
        f"Agar koi game ki baat kare toh full excited hoke bolna. "
        f"IMPORTANT: Reply sirf 1 line ka hona chahiye. Short and crisp."
    )

    # 2. Retry Logic (Keys Rotate karega)
    for _ in range(len(available_keys)):
        try:
            # Current Key uthao
            # Safety check: Index range se bahar na jaye
            if current_key_index >= len(available_keys): current_key_index = 0
            
            api_key = available_keys[current_key_index]
            genai.configure(api_key=api_key)
            
            # 🔥 Note: 'gemini-2.5' abhi public nahi hai, isliye 1.5-flash use kar rahe hain
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Chat Generation
            response = model.generate_content(f"{system_instruction}\n\nUser: {user_text}\nYuki:")
            
            if not response.text: raise Exception("Empty Response")
            
            return response.text.strip()
            
        except Exception as e:
            print(f"⚠️ Key Failed: {e}")
            # Agli key try karo
            get_next_key(available_keys)
            continue

    return "Yaar server lag kar raha hai... baad me aana. (All Keys Quota Exceeded)"
    
