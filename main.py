import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# IMPORTS
from config import TELEGRAM_TOKEN
from database import users_col, codes_col, update_balance, get_balance, check_registered, register_user, update_group_activity, update_username
from ai_chat import get_yuki_response

# MODULES (🔥 Added grouptools)
import admin, start, help, group, leaderboard, pay, bank, bet, wordseek, grouptools

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

async def ensure_registered(update, context):
    user = update.effective_user
    if not check_registered(user.id):
        register_user(user.id, user.first_name)
    return True

# --- COMMANDS ---

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        target = update.effective_user

    if target.is_bot:
        await update.message.reply_text("🤖 Bots ke paas paise nahi hote bhai!")
        return

    bal = get_balance(target.id)
    
    if target.id == update.effective_user.id:
        await update.message.reply_text(f"💳 **Your Balance:** ₹{bal}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"💳 **{target.first_name}'s Balance:** ₹{bal}", parse_mode=ParseMode.MARKDOWN)

async def redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not check_registered(user.id): register_user(user.id, user.first_name)
    
    if not context.args: 
        msg = await update.message.reply_text("⚠️ Usage: `/redeem <code>`")
        context.job_queue.run_once(delete_job, 5, chat_id=msg.chat_id, data=msg.message_id)
        return

    code_name = context.args[0].strip()
    code_data = codes_col.find_one({"code": code_name})
    
    if not code_data: return await update.message.reply_text("❌ Invalid Code!")
    if user.id in code_data.get("redeemed_by", []): return await update.message.reply_text("⚠️ Already redeemed!")
    if len(code_data.get("redeemed_by", [])) >= code_data.get("limit", 0): return await update.message.reply_text("❌ Code Expired!")
    
    amount = code_data["amount"]
    update_balance(user.id, amount)
    codes_col.update_one({"code": code_name}, {"$push": {"redeemed_by": user.id}})
    
    await update.message.reply_text(f"🎉 **Redeemed!**\nAdded: ₹{amount}\nBalance: ₹{get_balance(user.id)}", parse_mode=ParseMode.MARKDOWN)

async def shop_menu(update, context):
    user = update.effective_user
    if not check_registered(user.id): register_user(user.id, user.first_name)
    
    uid = user.id
    try:
        await update.message.delete()
    except:
        pass
    
    kb = []
    for k, v in SHOP_ITEMS.items():
        kb.append([InlineKeyboardButton(f"{v['name']} - ₹{v['price']}", callback_data=f"buy_{k}_{uid}")])
    kb.append([InlineKeyboardButton("❌ Close", callback_data=f"close_{uid}")])
    await update.message.reply_text("🛒 **VIP SHOP**", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# --- CALLBACK HANDLER ---
async def callback_handler(update, context):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    
    # 1. ADMIN PANEL
    if data.startswith("admin_"):
        await admin.admin_callback(update, context)
        return

    # 2. WORD SEEK GAME
    if data.startswith(("wrank_", "new_wordseek_", "close_wrank")):
        await wordseek.wordseek_callback(update, context)
        return

    # 3. START MENU
    if data.startswith(("help_", "start_chat_ai", "back_home")):
        await start.start_callback(update, context)
        return

    # 4. BET LOGIC
    if data.startswith(("set_", "clk_", "cash_", "close_", "noop_", "rebet_")):
        await bet.bet_callback(update, context)
        return

    # 5. REVIVE LOGIC
    if data.startswith("revive_"):
        await pay.revive_callback(update, context)
        return

    # 6. REGISTER
    if data.startswith("reg_start_"):
        target_id = int(data.split("_")[2])
        if uid != target_id: return await q.answer("Not for you!", show_alert=True)
        if register_user(uid, q.from_user.first_name): await q.edit_message_text("✅ Registered!")
        else: await q.answer("Already registered!")
        return

    # 7. SHOP
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

# --- MESSAGE HANDLER (TEXT & MEDIA) ---
async def handle_message(update, context):
    user = update.effective_user
    chat = update.effective_chat
    
    # 🔥 1. ADMIN INPUT CHECK 🔥
    if await admin.handle_admin_input(update, context):
        return
    
    # 🔥 2. WORD SEEK GUESS CHECK 🔥
    await wordseek.handle_word_guess(update, context)

    if not update.message: return
    text = update.message.text if update.message.text else ""

    # Update Data
    update_username(user.id, user.first_name)
    if chat.type in ["group", "supergroup"]:
        update_group_activity(chat.id, chat.title)

    # Chat Logic (Mimi/Yuki)
    if not text: return

    should_reply = False
    if chat.type == "private":
        should_reply = True
    elif chat.type in ["group", "supergroup"]:
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            should_reply = True
        elif "mimi" in text.lower() or "yuki" in text.lower():
            should_reply = True
        elif context.bot.username in text:
            should_reply = True

    if should_reply:
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        ai_reply = get_yuki_response(user.id, text, user.first_name)
        await update.message.reply_text(ai_reply)

# --- MAIN ---
def main():
    keep_alive()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", help.help_command))
    app.add_handler(CommandHandler("admin", admin.admin_panel))
    
    app.add_handler(CommandHandler("bal", balance_cmd))
    app.add_handler(CommandHandler("redeem", redeem_code))
    app.add_handler(CommandHandler("shop", shop_menu))
    app.add_handler(CommandHandler("bet", bet.bet_menu))
    
    app.add_handler(CommandHandler("bank", bank.bank_info))
    app.add_handler(CommandHandler("deposit", bank.deposit))
    app.add_handler(CommandHandler("withdraw", bank.withdraw))
    app.add_handler(CommandHandler("loan", bank.take_loan))
    app.add_handler(CommandHandler("payloan", bank.repay_loan))
    
    app.add_handler(CommandHandler("ranking", group.ranking))
    app.add_handler(CommandHandler("market", group.market_info))
    app.add_handler(CommandHandler("invest", group.invest))
    app.add_handler(CommandHandler("sell", group.sell_shares))
    app.add_handler(CommandHandler("top", leaderboard.user_leaderboard))
    
    app.add_handler(CommandHandler("pay", pay.pay_user))
    app.add_handler(CommandHandler("rob", pay.rob_user))
    app.add_handler(CommandHandler("kill", pay.kill_user))
    app.add_handler(CommandHandler("protect", pay.protect_user))
    app.add_handler(CommandHandler("alive", pay.check_status))
    
    # 🔥 WORD SEEK HANDLERS 🔥
    app.add_handler(CommandHandler("new", wordseek.start_wordseek))
    app.add_handler(CommandHandler("end", wordseek.stop_wordseek))
    app.add_handler(CommandHandler("wrank", wordseek.wordseek_rank))
    
    # 🔥 GROUP TOOLS HANDLERS (Regex for . and /) 🔥
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]warn$'), grouptools.warn_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]unwarn$'), grouptools.unwarn_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]mute$'), grouptools.mute_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]unmute$'), grouptools.unmute_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]ban$'), grouptools.ban_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]unban$'), grouptools.unban_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]kick$'), grouptools.kick_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]promote'), grouptools.promote_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]demote$'), grouptools.demote_user))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]title'), grouptools.set_title))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]pin$'), grouptools.pin_message))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]unpin$'), grouptools.unpin_message))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]d$'), grouptools.delete_msg))
    app.add_handler(MessageHandler(filters.Regex(r'^[\./]help$'), grouptools.admin_help))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Welcome & Messages
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group.welcome_user))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    
    print("🚀 BOT STARTED SUCCESSFULLY!")
    app.run_polling()

if __name__ == "__main__":
    main()
