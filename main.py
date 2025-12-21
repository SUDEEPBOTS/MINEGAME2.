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
    update_username, update_chat_stats,
    is_user_muted, is_user_banned
)
from ai_chat import get_yuki_response, get_mimi_sticker
from tts import generate_voice 

# MODULES
import admin, start, help, group, leaderboard, pay, bet, wordseek, grouptools, chatstat, logger, events

# 🔥 Bank Updated Import
import bank 
from bank import check_balance 

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
    try: await context.bot.delete_message(context.job.chat_id, context.job.data)
    except: pass

# --- SHOP MENU ---
async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic to handle both Command and Button Click
    if update.callback_query:
        uid = update.callback_query.from_user.id
        # Button click me EDIT karna better lagta hai
        msg_func = update.callback_query.message.edit_text 
    else:
        uid = update.effective_user.id
        msg_func = update.message.reply_text

    kb = []
    for k, v in SHOP_ITEMS.items():
        kb.append([InlineKeyboardButton(f"{v['name']} - ₹{v['price']}", callback_data=f"buy_{k}_{uid}")])
    kb.append([InlineKeyboardButton("❌ Close", callback_data=f"close_help")])
    
    await msg_func("🛒 **VIP SHOP**\nBuy special titles here:", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args: return await update.message.reply_text("⚠️ Usage: `/redeem CODE`")
    
    code = context.args[0]
    data = codes_col.find_one({"code": code})
    if not data: return await update.message.reply_text("❌ Invalid Code!")
    if user.id in data["redeemed_by"]: return await update.message.reply_text("⚠️ Already Redeemed!")
    
    update_balance(user.id, data["amount"])
    codes_col.update_one({"code": code}, {"$push": {"redeemed_by": user.id}})
    await update.message.reply_text(f"🎉 Redeemed ₹{data['amount']}!")

# --- CALLBACK HANDLER (ALL BUTTONS FIXED) ---
async def callback_handler(update, context):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    
    # 1. UI CLOSE ACTIONS
    if data in ["close_log", "close_ping", "close_help"]:
        try: await q.message.delete()
        except: pass
        return

    # 2. START MENU BUTTONS (Routing)
    # Ye codes Start Message ke buttons se match hone chahiye
    if data == "open_shop":
        await q.answer()
        await shop_menu(update, context)
        return
    
    if data == "open_games":
        await q.answer()
        # Games ka help menu dikhao
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        msg = "🎮 **GAME MENU**\n\n🎲 `/bet` - Bomb Game\n🔠 `/new` - Word Seek\n💰 `/invest` - Stock Market"
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "open_ranking":
        await q.answer()
        # Leaderboard call karo (Updated leaderboard.py zaroori hai)
        await leaderboard.user_leaderboard(update, context)
        return

    if data == "open_commands":
        await q.answer()
        await help.help_callback(update, context) # Redirect to Help
        return
    
    if data == "back_home":
        await q.answer()
        await start.start_callback(update, context)
        return

    # 3. HELP MODULES
    if data.startswith(("help_", "mod_")): 
        await help.help_callback(update, context)
        return
        
    if data.startswith(("start_", "st_")):
        await start.start_callback(update, context)
        return

    # 4. ADMIN PANEL
    if data.startswith("admin_"):
        await admin.admin_callback(update, context)
        return

    # 5. WORD SEEK GAME
    if data.startswith(("wrank_", "new_wordseek_", "close_wrank", "end_wordseek")):
        await wordseek.wordseek_callback(update, context)
        return

    # 6. CHAT STATS
    if data.startswith(("rank_", "hide_rank")):
        await chatstat.rank_callback(update, context)
        return
        
    # 7. BET & GAMES
    if data.startswith(("set_", "clk_", "cash_", "close_", "noop_", "rebet_")):
        await bet.bet_callback(update, context)
        return

    # 8. REGISTRATION & SHOP BUYING
    if data.startswith("reg_start_"):
        if uid != int(data.split("_")[2]): return await q.answer("Not for you!", show_alert=True)
        if register_user(uid, q.from_user.first_name): await q.edit_message_text("✅ Registered!")
        else: await q.answer("Already registered!")
        return

    if data.startswith("buy_"):
        parts = data.split("_")
        if uid != int(parts[2]): return await q.answer("Not for you!", show_alert=True)
        item = SHOP_ITEMS.get(parts[1])
        if get_balance(uid) < item["price"]: return await q.answer("No Money!", show_alert=True)
        update_balance(uid, -item["price"])
        users_col.update_one({"_id": uid}, {"$push": {"titles": item["name"]}})
        await q.answer(f"Bought {item['name']}!")
        # await q.message.delete() # Shop band nahi karte, taaki aur khareed sake
        return
    
    # 9. REVIVE
    if data.startswith("revive_"):
        await pay.revive_callback(update, context)
        return

# --- MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. ENFORCEMENT
    if chat.type in ["group", "supergroup"] and not user.is_bot:
        if is_user_banned(chat.id, user.id) or is_user_muted(chat.id, user.id):
            try: await update.message.delete()
            except: pass
            return

    # 2. ANTI-SPAM
    if not user.is_bot:
        status = check_spam(user.id)
        if status == "BLOCKED":
            await update.message.reply_text(f"🚫 **Spam Detected!**\n{user.first_name}, blocked for 8 mins.")
            return
        elif status == False: return

    # 3. STATS
    update_username(user.id, user.first_name)
    if chat.type in ["group", "supergroup"] and not user.is_bot:
        update_chat_stats(chat.id, user.id, user.first_name)
        update_group_activity(chat.id, chat.title)

    # 4. ADMIN & WORD GUESS
    if await admin.handle_admin_input(update, context): return
    await wordseek.handle_word_guess(update, context)

    # 5. STICKER
    if update.message.sticker:
        if chat.type == "private" or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id) or random.random() < 0.2:
            sticker_id = await get_mimi_sticker(context.bot)
            if sticker_id: await update.message.reply_sticker(sticker_id)
        return

    # 6. TEXT & VOICE AI
    text = update.message.text
    if not text: return

    should_reply = False
    if chat.type == "private": should_reply = True
    elif any(trigger in text.lower() for trigger in ["mimi", "yuki", context.bot.username.lower()]): should_reply = True
    elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id: should_reply = True

    if should_reply:
        voice_triggers = ["voice", "audio", "bol", "bolo", "speak", "suna", "rec", "batao", "sunao", "kaho"]
        wants_voice = any(v in text.lower() for v in voice_triggers)

        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        ai_reply = get_yuki_response(user.id, text, user.first_name)

        if wants_voice:
            await context.bot.send_chat_action(chat_id=chat.id, action="record_voice")
            audio_path = await generate_voice(ai_reply)
            
            if audio_path:
                try:
                    with open(audio_path, 'rb') as voice_file:
                        await update.message.reply_voice(voice=voice_file)
                    os.remove(audio_path)
                    return
                except Exception as e:
                    print(f"Voice Send Error: {e}")
                    await update.message.reply_text(ai_reply)
            else:
                await update.message.reply_text(ai_reply)
        else:
            await update.message.reply_text(ai_reply)

# --- MAIN ENGINE ---
def main():
    keep_alive()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Core Commands
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", help.help_command))
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    
    # Economy
    app.add_handler(CommandHandler("bal", check_balance))
    app.add_handler(CommandHandler("redeem", redeem_code))
    app.add_handler(CommandHandler("shop", shop_menu))
    
    # Leaderboard & Stats
    app.add_handler(CommandHandler("top", leaderboard.user_leaderboard))
    app.add_handler(CommandHandler("ranking", group.ranking))
    app.add_handler(CommandHandler("stats", logger.stats_bot))
    app.add_handler(CommandHandler("ping", logger.ping_bot))
    
    # Games & Market
    app.add_handler(CommandHandler("bet", bet.bet_menu))
    app.add_handler(CommandHandler("new", wordseek.start_wordseek))
    app.add_handler(CommandHandler("market", group.market_info))
    app.add_handler(CommandHandler("invest", group.invest))
    app.add_handler(CommandHandler("sell", group.sell_shares))
    app.add_handler(CommandHandler("topinvest", group.top_investors))
    
    # Banking
    app.add_handler(CommandHandler("bank", bank.bank_info))
    app.add_handler(CommandHandler("deposit", bank.deposit))
    app.add_handler(CommandHandler("withdraw", bank.withdraw))
    app.add_handler(CommandHandler("loan", bank.take_loan))
    app.add_handler(CommandHandler("payloan", bank.repay_loan))
    
    # Pay & RPG
    app.add_handler(CommandHandler("pay", pay.pay_user))
    app.add_handler(CommandHandler("rob", pay.rob_user))
    app.add_handler(CommandHandler("kill", pay.kill_user))
    app.add_handler(CommandHandler("protect", pay.protect_user))
    app.add_handler(CommandHandler("alive", pay.check_status))

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
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]unmute$'), grouptools.unmute_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]ban$'), grouptools.ban_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]unban$'), grouptools.unban_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]kick$'), grouptools.kick_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]pin$'), grouptools.pin_message))
    
    # Message Logic (AI)
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    
    print("🚀 MIMI BOT STARTED SUCCESSFULLY!")
    app.run_polling()

if __name__ == "__main__":
    main()
