import pymongo
import time
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
    game_keys_col = db["game_keys"]  # 🔥 Game Keys (New)
    settings_col = db["settings"]
    wordseek_col = db["wordseek_scores"] # 🔥 WordSeek Scores (New)

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
    wordseek_col.delete_many({}) # Score bhi wipe honge
    return True

# --- GROUP & MARKET ---

def update_group_activity(group_id, group_name):
    groups_col.update_one(
        {"_id": group_id},
        {"$set": {"name": group_name}, "$inc": {"activity": 1}},
        upsert=True
    )

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

# --- 🔥 GAME API KEYS (WordSeek) 🔥 ---

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

# --- 🔥 WORDSEEK SCORES 🔥 ---

def update_wordseek_score(user_id, name, points, group_id):
    """Updates Global & Group specific scores"""
    # 1. Update Global
    wordseek_col.update_one(
        {"_id": user_id},
        {
            "$inc": {"global_score": points},
            "$set": {"name": name}
        },
        upsert=True
    )
    # 2. Update Group (Nested Field)
    wordseek_col.update_one(
        {"_id": user_id},
        {
            "$inc": {f"group_scores.{group_id}": points}
        }
    )

def get_wordseek_leaderboard(group_id=None):
    """Returns Top 10 Players"""
    if group_id:
        # Group Rank
        cursor = wordseek_col.find({f"group_scores.{group_id}": {"$exists": True}})
        data = list(cursor)
        # Sort by Group Score
        data.sort(key=lambda x: x.get("group_scores", {}).get(str(group_id), 0), reverse=True)
        return data[:10]
    else:
        # Global Rank
        cursor = wordseek_col.find().sort("global_score", -1).limit(10)
        return list(cursor)
