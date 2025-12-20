import pymongo
import time
import datetime # 🔥 Import for Date/Time Logic
from config import MONGO_URL

# --- DATABASE CONNECTION ---
try:
    client = pymongo.MongoClient(MONGO_URL)
    db = client["CasinoBot"]

    # Collections
    users_col = db["users"]
    groups_col = db["groups"]
    investments_col = db["investments"]
    codes_col = db["codes"]
    keys_col = db["api_keys"]        # Chat Keys
    game_keys_col = db["game_keys"]  # Game Keys
    settings_col = db["settings"]
    wordseek_col = db["wordseek_scores"] 
    warnings_col = db["warnings"]    # Warnings
    packs_col = db["sticker_packs"]  # Sticker Packs
    chat_stats_col = db["chat_stats"] # 🔥 Chat Stats (Ranking)

    print("✅ Database Connected!")
except Exception as e:
    print(f"❌ DB Error: {e}")

# --- USER FUNCTIONS ---

def update_username(user_id, name):
    """Har message par naam update karega"""
    users_col.update_one({"_id": user_id}, {"$set": {"name": name}}, upsert=True)

def check_registered(user_id):
    """Check if user exists"""
    return users_col.find_one({"_id": user_id}) is not None

def register_user(user_id, name):
    """Register new user"""
    if check_registered(user_id): 
        update_username(user_id, name)
        return False

    user = {
        "_id": user_id, 
        "name": name, 
        "balance": 500,       
        "bank_balance": 0,    
        "loan": 0,            
        "titles": [],
        "kills": 0,
        "protection": 0,
        "is_dead": False      
    } 
    users_col.insert_one(user)
    return True

def get_user(user_id):
    return users_col.find_one({"_id": user_id})

def update_balance(user_id, amount):
    users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)

def get_balance(user_id):
    user = users_col.find_one({"_id": user_id})
    return user["balance"] if user else 0

# --- BANK FUNCTIONS ---

def get_bank_balance(user_id):
    user = users_col.find_one({"_id": user_id})
    return user.get("bank_balance", 0) if user else 0

def update_bank_balance(user_id, amount):
    users_col.update_one({"_id": user_id}, {"$inc": {"bank_balance": amount}}, upsert=True)

def get_loan(user_id):
    user = users_col.find_one({"_id": user_id})
    return user.get("loan", 0) if user else 0

def set_loan(user_id, amount):
    users_col.update_one({"_id": user_id}, {"$set": {"loan": amount}}, upsert=True)

# --- CRIME & STATUS FUNCTIONS ---

def update_kill_count(user_id):
    users_col.update_one({"_id": user_id}, {"$inc": {"kills": 1}}, upsert=True)

def set_dead(user_id, status: bool):
    users_col.update_one({"_id": user_id}, {"$set": {"is_dead": status}}, upsert=True)

def is_dead(user_id):
    user = users_col.find_one({"_id": user_id})
    return user.get("is_dead", False) if user else False

def set_protection(user_id, duration_hours):
    expiry = time.time() + (duration_hours * 3600)
    users_col.update_one({"_id": user_id}, {"$set": {"protection": expiry}}, upsert=True)

def is_protected(user_id):
    user = users_col.find_one({"_id": user_id})
    if not user or "protection" not in user: return False
    return time.time() < user["protection"]

# --- ECONOMY & ADMIN ---

def get_economy_status():
    status = settings_col.find_one({"_id": "economy_status"})
    if not status: return True 
    return status["active"]

def set_economy_status(status: bool):
    settings_col.update_one({"_id": "economy_status"}, {"$set": {"active": status}}, upsert=True)

def wipe_database():
    """⚠️ DANGER: Reset Everything"""
    users_col.delete_many({})
    investments_col.delete_many({})
    wordseek_col.delete_many({}) 
    warnings_col.delete_many({})
    packs_col.delete_many({})
    chat_stats_col.delete_many({}) # Chat Stats bhi clear
    groups_col.delete_many({})     # Groups bhi clear
    return True

# --- GROUP & MARKET ---

def update_group_activity(group_id, group_name):
    groups_col.update_one(
        {"_id": group_id},
        {"$set": {"name": group_name}, "$inc": {"activity": 1}},
        upsert=True
    )

# 🔥 NEW: REMOVE GROUP FROM DB (For Accurate Stats)
def remove_group(group_id):
    """Jab Bot group se nikle, to DB se bhi hata do"""
    groups_col.delete_one({"_id": group_id})
    # Optional: Chat Stats bhi clear karne hain to niche wali line uncomment karo
    # chat_stats_col.delete_many({"group_id": group_id})

def get_group_price(group_id):
    grp = groups_col.find_one({"_id": group_id})
    if not grp: return 10.0
    return round(10 + (grp.get("activity", 0) * 0.5), 2)

# --- CHAT API KEYS (Mimi) ---

def add_api_key(api_key):
    if keys_col.find_one({"key": api_key}): return False 
    keys_col.insert_one({"key": api_key})
    return True

def remove_api_key(api_key):
    result = keys_col.delete_one({"key": api_key})
    return result.deleted_count > 0

def get_all_keys():
    keys = list(keys_col.find({}, {"_id": 0, "key": 1}))
    return [k["key"] for k in keys]

# --- GAME API KEYS (WordSeek) ---

def add_game_key(api_key):
    if game_keys_col.find_one({"key": api_key}): return False 
    game_keys_col.insert_one({"key": api_key})
    return True

def remove_game_key(api_key):
    result = game_keys_col.delete_one({"key": api_key})
    return result.deleted_count > 0

def get_game_keys():
    keys = list(game_keys_col.find({}, {"_id": 0, "key": 1}))
    return [k["key"] for k in keys]

# --- WORDSEEK SCORES ---

def update_wordseek_score(user_id, name, points, group_id):
    # 1. Update Global
    wordseek_col.update_one(
        {"_id": user_id},
        {
            "$inc": {"global_score": points},
            "$set": {"name": name}
        },
        upsert=True
    )
    # 2. Update Group
    wordseek_col.update_one(
        {"_id": user_id},
        {
            "$inc": {f"group_scores.{group_id}": points}
        }
    )

def get_wordseek_leaderboard(group_id=None):
    if group_id:
        cursor = wordseek_col.find({f"group_scores.{group_id}": {"$exists": True}})
        data = list(cursor)
        data.sort(key=lambda x: x.get("group_scores", {}).get(str(group_id), 0), reverse=True)
        return data[:10]
    else:
        cursor = wordseek_col.find().sort("global_score", -1).limit(10)
        return list(cursor)

# --- GROUP TOOLS (WARNINGS) ---

def add_warning(group_id, user_id):
    """Warning add karta hai aur count return karta hai"""
    data = warnings_col.find_one({"group_id": group_id, "user_id": user_id})
    if data:
        new_count = data["count"] + 1
        warnings_col.update_one({"_id": data["_id"]}, {"$set": {"count": new_count}})
        return new_count
    else:
        warnings_col.insert_one({"group_id": group_id, "user_id": user_id, "count": 1})
        return 1

def remove_warning(group_id, user_id):
    """1 Warning kam karta hai"""
    data = warnings_col.find_one({"group_id": group_id, "user_id": user_id})
    if data and data["count"] > 0:
        new_count = data["count"] - 1
        if new_count == 0:
            warnings_col.delete_one({"_id": data["_id"]})
        else:
            warnings_col.update_one({"_id": data["_id"]}, {"$set": {"count": new_count}})
        return new_count
    return 0

def reset_warnings(group_id, user_id):
    """Warnings clean karta hai (Ban ke baad)"""
    warnings_col.delete_one({"group_id": group_id, "user_id": user_id})

# --- STICKER PACKS ---

def add_sticker_pack(pack_name):
    """Sticker Pack ka naam save karega"""
    if not packs_col.find_one({"name": pack_name}):
        packs_col.insert_one({"name": pack_name})
        return True
    return False

def remove_sticker_pack(pack_name):
    """Pack remove karega"""
    if packs_col.find_one({"name": pack_name}):
        packs_col.delete_one({"name": pack_name})
        return True
    return False

def get_sticker_packs():
    """Saare packs ki list dega"""
    data = list(packs_col.find())
    return [d["name"] for d in data]

# --- 🔥 CHAT STATS & RANKING (NEW) 🔥 ---

def update_chat_stats(group_id, user_id, name):
    """
    Updates message count.
    Auto-resets 'today' (Daily) and 'week' (Weekly) counts based on date.
    """
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    week_str = now.strftime("%Y-%W") # Year-WeekNumber

    # Find existing data
    data = chat_stats_col.find_one({"group_id": group_id, "user_id": user_id})

    if not data:
        # New Entry
        chat_stats_col.insert_one({
            "group_id": group_id,
            "user_id": user_id,
            "name": name,
            "overall": 1,
            "today": 1,
            "week": 1,
            "last_date": today_str,
            "last_week": week_str
        })
    else:
        # Prepare Update
        update_query = {"$inc": {"overall": 1}, "$set": {"name": name}}
        
        # Check Day Reset
        if data.get("last_date") != today_str:
            update_query["$set"]["today"] = 1 # Reset to 1
            update_query["$set"]["last_date"] = today_str
        else:
            update_query["$inc"]["today"] = 1
            
        # Check Week Reset
        if data.get("last_week") != week_str:
            update_query["$set"]["week"] = 1 # Reset to 1
            update_query["$set"]["last_week"] = week_str
        else:
            update_query["$inc"]["week"] = 1

        chat_stats_col.update_one({"_id": data["_id"]}, update_query)

def get_top_chatters(group_id, mode="overall"):
    """
    mode: 'overall', 'today', 'week'
    Returns Top 10 users sorted by mode.
    """
    cursor = chat_stats_col.find({"group_id": group_id}).sort(mode, -1).limit(10)
    return list(cursor)

def get_total_messages(group_id):
    """Group ke total messages count karega"""
    pipeline = [
        {"$match": {"group_id": group_id}},
        {"$group": {"_id": None, "total": {"$sum": "$overall"}}}
    ]
    result = list(chat_stats_col.aggregate(pipeline))
    return result[0]["total"] if result else 0

# --- 🔥 LOGGER SETTINGS (Re-added for Logger) 🔥 ---

def set_logger_group(group_id):
    """Logger Group ID save karega"""
    settings_col.update_one(
        {"_id": "logger_settings"},
        {"$set": {"group_id": int(group_id)}},
        upsert=True
    )

def get_logger_group():
    """Logger Group ID layega"""
    data = settings_col.find_one({"_id": "logger_settings"})
    return data["group_id"] if data else None

def delete_logger_group():
    """Logger ID delete karega"""
    settings_col.delete_one({"_id": "logger_settings"})

# --- 🔥 GLOBAL STATS (For Logger .stats) 🔥 ---

def get_total_users():
    return users_col.count_documents({})

def get_total_groups():
    return groups_col.count_documents({})
