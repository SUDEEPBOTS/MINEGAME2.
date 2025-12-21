import pymongo
import time
import datetime
from config import MONGO_URL

# --- DATABASE CONNECTION ---
try:
    client = pymongo.MongoClient(MONGO_URL)
    db = client["CasinoBot"]

    # Existing Collections
    users_col = db["users"]
    groups_col = db["groups"]
    investments_col = db["investments"]
    codes_col = db["codes"]
    keys_col = db["api_keys"]        
    game_keys_col = db["game_keys"]  
    settings_col = db["settings"]
    wordseek_col = db["wordseek_scores"] 
    warnings_col = db["warnings"]    
    packs_col = db["sticker_packs"]  
    chat_stats_col = db["chat_stats"] 

    # 🔥 NEW: Moderation Collections
    mutes_col = db["mutes"]  # For tracking muted users
    bans_col = db["bans"]    # For tracking banned users (Global or Group)

    print("✅ Database Connected!")
except Exception as e:
    print(f"❌ DB Error: {e}")

# --- USER FUNCTIONS (Standard) ---
# ... (Keep your existing update_username, register_user, update_balance, etc.)

# --- 🔥 NEW: MUTE & BAN FUNCTIONS (RELIABLE ENFORCEMENT) ---

def mute_user_db(group_id, user_id, duration_mins=None):
    """Mutes a user in the database. If duration is None, it's permanent until unmuted."""
    expiry = (time.time() + (duration_mins * 60)) if duration_mins else None
    mutes_col.update_one(
        {"group_id": group_id, "user_id": user_id},
        {"$set": {"expiry": expiry}},
        upsert=True
    )

def unmute_user_db(group_id, user_id):
    """Removes the mute record from database."""
    mutes_col.delete_one({"group_id": group_id, "user_id": user_id})

def is_user_muted(group_id, user_id):
    """Checks if a user is muted and handles expiry."""
    mute_data = mutes_col.find_one({"group_id": group_id, "user_id": user_id})
    if not mute_data:
        return False
    
    expiry = mute_data.get("expiry")
    if expiry and time.time() > expiry:
        unmute_user_db(group_id, user_id)
        return False
    return True

def ban_user_db(group_id, user_id, reason="No reason provided"):
    """Saves ban status to DB to prevent rejoin/re-entry issues."""
    bans_col.update_one(
        {"group_id": group_id, "user_id": user_id},
        {"$set": {"reason": reason, "time": time.time()}},
        upsert=True
    )

def unban_user_db(group_id, user_id):
    """Removes ban status from DB."""
    bans_col.delete_one({"group_id": group_id, "user_id": user_id})

def is_user_banned(group_id, user_id):
    """Checks if user is in the banned list for this group."""
    return bans_col.find_one({"group_id": group_id, "user_id": user_id}) is not None

# --- IMPROVED WARNING LOGIC ---

def add_warning(group_id, user_id):
    """Warning add karta hai aur count return karta hai. Max 3 logic can be used in main.py"""
    data = warnings_col.find_one({"group_id": group_id, "user_id": user_id})
    if data:
        new_count = data["count"] + 1
        warnings_col.update_one({"_id": data["_id"]}, {"$set": {"count": new_count}})
        return new_count
    else:
        warnings_col.insert_one({"group_id": group_id, "user_id": user_id, "count": 1})
        return 1

def get_warnings(group_id, user_id):
    """Returns the current warning count for a user."""
    data = warnings_col.find_one({"group_id": group_id, "user_id": user_id})
    return data["count"] if data else 0

# --- GROUP PERMISSIONS ---

def set_group_setting(group_id, setting_name, value):
    """Dynamically set group-specific settings (e.g., 'anti_link': True)"""
    groups_col.update_one(
        {"_id": group_id},
        {"$set": {f"settings.{setting_name}": value}},
        upsert=True
    )

def get_group_setting(group_id, setting_name, default=False):
    """Retrieve group-specific settings."""
    group = groups_col.find_one({"_id": group_id})
    if group and "settings" in group:
        return group["settings"].get(setting_name, default)
    return default

# --- EXISTING GROUP & MARKET FUNCTIONS ---
# ... (Keep your update_group_activity, remove_group, etc.)

# --- WIPE DATA (UPDATED) ---

def wipe_database():
    """⚠️ DANGER: Reset Everything Including Bans and Mutes"""
    users_col.delete_many({})
    investments_col.delete_many({})
    wordseek_col.delete_many({}) 
    warnings_col.delete_many({})
    packs_col.delete_many({})
    chat_stats_col.delete_many({})
    groups_col.delete_many({})
    mutes_col.delete_many({})  # Clear Mutes
    bans_col.delete_many({})   # Clear Bans
    return True

# --- GLOBAL STATS ---
# ... (Keep your get_total_users, get_total_groups)
