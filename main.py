import random
import os
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# IMPORTS
from config import TELEGRAM_TOKEN
from database import (
    users_col, codes_col, update_balance, get_balance, 
    check_registered, register_user, update_group_activity, 
    update_username, update_chat_stats
)
from ai_chat import get_yuki_response, get_mimi_sticker
from tts import generate_voice 

# MODULES
import admin, start, help, group, leaderboard, pay, bank, bet, wordseek, grouptools, chatstat, logger, events

# 🔥 Import Anti-Spam
from antispam import check_spam

# --- FLASK SERVER ---
app = Flask('')
@app.route('/')
def home(): return "I am Alive! 24/7"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): t = Thread(target=run); t.start()

# VARS
SHOP_ITEMS = {
    "vip":   {"name": "👑 VIP", "price": 10000},
    "god":   {"name": "⚡ God", "price": 50000},
    "rich":  {"name": "💸 Rich", "price": 100000}
}

async def delete_job(context):
    try:
        await context.bot.delete_message(context.job.chat_id, context.job.data)
    except:
        pass

# --- CALLBACK HANDLER (FIXED INDENTATION) ---
async def callback_handler(update, context):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    
    # 1. UI CLOSE ACTIONS
    if data in ["close_log", "close_ping", "close_help"]:
        await q.message.delete()
        return

    # 2. ADMIN PANEL
    if data.startswith("admin_"):
        await admin.admin_callback(update, context)
        return

    # 3. WORD SEEK GAME
    if data.startswith(("wrank_", "new_wordseek_", "close_wrank", "end_wordseek")):
        await wordseek.wordseek_callback(update, context)
        return

    # 4. HELP & START MENU (Separated)
    if data.startswith("help_"):
        await help.help_callback(update, context)
        return
    if data.startswith(("start_chat_ai", "back_home")):
        await start.start_callback(update, context)
        return

    # 5. CHAT STATS & RANKING
    if data.startswith(("rank_", "hide_rank")):
        await chatstat.rank_callback(update, context)
        return
        
    # 6. BET & GAMES
    if data.startswith(("set_", "clk_", "cash_", "close_", "noop_", "rebet_")):
        await bet.bet_callback(update, context)
        return

    # 7. REGISTRATION & SHOP
    if data.startswith("reg_start_"):
        target_id = int(data.split("_")[2])
        if uid != target_id: 
            return await q.answer("Not for you!", show_alert=True)
        if register_user(uid, q.from_user.first_name): 
            await q.edit_message_text("✅ Registered!")
        else:
            await q.answer("Already registered!")
        return

    if data.startswith("buy_"):
        parts = data.split("_")
        target_id = int(parts[2])
        if uid != target_id: return await q.answer("Not for you!", show_alert=True)
        item = SHOP_ITEMS.get(parts[1])
        if get_balance(uid) < item["price"]: return await q.answer("No Money!", show_alert=True)
        update_balance(uid, -item["price"])
        users_col.update_one({"_id": uid}, {"$push": {"titles": item["name"]}})
        await q.answer(f"Bought {item['name']}!")
        await q.message.delete()
        return

# --- MESSAGE HANDLER (AI & VOICE) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. ANTI-SPAM
    if not user.is_bot:
        status = check_spam(user.id)
        if status == "BLOCKED":
            await update.message.reply_text(f"🚫 **Spam Detected!**\n{user.first_name}, you are blocked for 8 minutes.")
            return
        elif status == False: return

    # 2. DB UPDATE & STATS
    update_username(user.id, user.first_name)
    if chat.type in ["group", "supergroup"] and not user.is_bot:
        update_chat_stats(chat.id, user.id, user.first_name)
        update_group_activity(chat.id, chat.title)

    # 3. ADMIN & WORD GUESS
    if await admin.handle_admin_input(update, context): return
    await wordseek.handle_word_guess(update, context)

    # 4. STICKER LOGIC
    if update.message.sticker:
        if chat.type == "private" or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id) or random.random() < 0.2:
            sticker_id = await get_mimi_sticker(context.bot)
            if sticker_id: await update.message.reply_sticker(sticker_id)
        return

    # 5. TEXT & VOICE AI
    text = update.message.text
    if not text: return

    should_reply = False
    if chat.type == "private": should_reply = True
    elif any(trigger in text.lower() for trigger in ["mimi", "yuki", context.bot.username.lower()]): should_reply = True
    elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_reply = True

    if should_reply:
        voice_triggers = ["voice", "audio", "bol", "bolo", "speak", "suna", "rec", "batao"]
        wants_voice = any(v in text.lower() for v in voice_triggers)

        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        ai_reply = get_yuki_response(user.id, text, user.first_name)

        if wants_voice:
            await context.bot.send_chat_action(chat_id=chat.id, action="record_voice")
            audio_path = generate_voice(ai_reply)
            if audio_path:
                try:
                    await update.message.reply_voice(voice=open(audio_path, 'rb'), caption=f"🗣 **Mimi:** {ai_reply}")
                    os.remove(audio_path)
                    return
                except: pass
        
        await update.message.reply_text(ai_reply)

# --- MAIN ENGINE ---
def main():
    keep_alive()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handler Registration
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", help.help_command))
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    app.add_handler(CommandHandler("bal", admin.admin_panel)) # Optional balance alias
    
    # Leaderboard & Stats
    app.add_handler(CommandHandler("top", leaderboard.user_leaderboard))
    app.add_handler(CommandHandler("ranking", group.ranking))
    app.add_handler(CommandHandler("stats", logger.stats_bot))
    app.add_handler(CommandHandler("ping", logger.ping_bot))
    
    # Games & Economy
    app.add_handler(CommandHandler("bet", bet.bet_menu))
    app.add_handler(CommandHandler("new", wordseek.start_wordseek))
    app.add_handler(CommandHandler("bank", bank.bank_info))
    
    # Callback Handlers
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Event Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, events.welcome_user))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, events.track_leave))
    app.add_handler(MessageHandler(filters.Regex(r'(?i)^[\./]crank'), chatstat.show_leaderboard))
    
    # Group Admin Tools
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]id$'), grouptools.get_id))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]warn$'), grouptools.warn_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]mute$'), grouptools.mute_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]ban$'), grouptools.ban_user))
    
    # Message Logic (AI)
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    
    print("🚀 MIMI BOT STARTED SUCCESSFULLY!")
    app.run_polling()

if __name__ == "__main__":
    main()
