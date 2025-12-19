from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from config import OWNER_ID
# 👇 Naye Database functions import kiye hain
from database import users_col, codes_col, update_balance, add_api_key, remove_api_key, get_all_keys

# --- EXISTING COMMANDS (Broadcast & Money) ---

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args: return await update.message.reply_text("⚠️ Message toh likho!")

    msg = " ".join(context.args)
    users = users_col.find({})
    count = 0
    for u in users:
        try: 
            await context.bot.send_message(u["_id"], f"📢 **NOTICE**\n\n{msg}", parse_mode=ParseMode.MARKDOWN)
            count += 1
        except: pass
    await update.message.reply_text(f"✅ Broadcast Sent to {count} users.")

async def create_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        codes_col.insert_one({
            "code": context.args[0], 
            "amount": int(context.args[1]), 
            "limit": int(context.args[2]), 
            "redeemed_by": []
        })
        await update.message.reply_text("✅ Code Created")
    except: await update.message.reply_text("⚠️ Format: `/code NAME AMOUNT LIMIT`")

async def add_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try: 
        update_balance(int(context.args[0]), int(context.args[1]))
        await update.message.reply_text("✅ Money Added")
    except: pass

async def take_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try: 
        update_balance(int(context.args[0]), -int(context.args[1]))
        await update.message.reply_text("✅ Money Taken")
    except: pass

# --- 🔥 NEW: API KEY COMMANDS ---

async def add_key_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to add Gemini API Key"""
    if update.effective_user.id != OWNER_ID: return
    
    try:
        new_key = context.args[0]
        if add_api_key(new_key):
            await update.message.reply_text("✅ **API Key Added!**", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ Ye Key pehle se added hai!")
    except:
        await update.message.reply_text("⚠️ Usage: `/addkey <AIzaSy...>`")
    
    # Security: Message delete kar do taaki key kisi aur ko na dikhe
    try: await update.message.delete()
    except: pass

async def remove_key_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to remove API Key"""
    if update.effective_user.id != OWNER_ID: return
    
    try:
        key_to_remove = context.args[0]
        if remove_api_key(key_to_remove):
            await update.message.reply_text("🗑 **API Key Removed!**", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Ye Key database me nahi mili.")
    except:
        await update.message.reply_text("⚠️ Usage: `/delkey <AIzaSy...>`")
    
    try: await update.message.delete()
    except: pass

async def list_keys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Count active keys"""
    if update.effective_user.id != OWNER_ID: return
    
    keys = get_all_keys()
    count = len(keys)
    # Hum keys show nahi karenge security ke liye, bas count batayenge
    await update.message.reply_text(f"🔑 **Total Active API Keys:** `{count}`", parse_mode=ParseMode.MARKDOWN)
    
