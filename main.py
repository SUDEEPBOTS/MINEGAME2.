import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# IMPORTS
from config import TELEGRAM_TOKEN
from database import users_col, codes_col, update_balance, get_balance, check_registered, register_user, update_group_activity
from ai_chat import get_yuki_response

# MODULES (Bet ab alag hai)
import admin, start, help, group, leaderboard, pay, bank, bet

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

async def ensure_registered(update, context):
    user = update.effective_user
    if not check_registered(user.id):
        kb = [[InlineKeyboardButton("📝 Register", callback_data=f"reg_start_{user.id}")]]
        await update.message.reply_text(f"🛑 **{user.first_name}, Register First!**\nGet ₹500 Bonus.", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN, quote=True)
        return False
    return True

# --- GROUP REWARD ---
async def group_join_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.new_chat_members: return
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            adder = update.message.from_user
            update_balance(adder.id, 1000)
            await update.message.reply_text(f"🎉 **Thanks {adder.first_name}!**\nAdded ₹1000 to your wallet!", quote=True)

# --- COMMANDS ---

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bal = get_balance(user.id)
    await update.message.reply_text(f"💳 **{user.first_name}'s Balance:** ₹{bal}", parse_mode=ParseMode.MARKDOWN, quote=True)

async def redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_registered(update, context): return
    user = update.effective_user
    
    # Check Argument
    if not context.args: 
        msg = await update.message.reply_text("⚠️ Usage: `/redeem <code>`", quote=True)
        context.job_queue.run_once(delete_job, 5, chat_id=msg.chat_id, data=msg.message_id)
        return

    # 🔥 FIX: Remove spaces
    code_name = context.args[0].strip()

    code_data = codes_col.find_one({"code": code_name})
    if not code_data: return await update.message.reply_text("❌ Invalid Code!", quote=True)
    if user.id in code_data.get("redeemed_by", []): return await update.message.reply_text("⚠️ Already redeemed!", quote=True)
    if len(code_data.get("redeemed_by", [])) >= code_data.get("limit", 0): return await update.message.reply_text("❌ Code Expired!", quote=True)
    
    amount = code_data["amount"]
    update_balance(user.id, amount)
    codes_col.update_one({"code": code_name}, {"$push": {"redeemed_by": user.id}})
    
    await update.message.reply_text(f"🎉 **Redeemed!**\nAdded: ₹{amount}\nBalance: ₹{get_balance(user.id)}", parse_mode=ParseMode.MARKDOWN, quote=True)

async def shop_menu(update, context):
    if not await ensure_registered(update, context): return
    uid = update.effective_user.id
    kb = []
    for k, v in SHOP_ITEMS.items():
        kb.append([InlineKeyboardButton(f"{v['name']} - ₹{v['price']}", callback_data=f"buy_{k}_{uid}")])
    kb.append([InlineKeyboardButton("❌ Close", callback_data=f"close_{uid}")])
    await update.message.reply_text("🛒 **VIP SHOP**", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN, quote=True)

# --- CALLBACK HANDLER ---
async def callback_handler(update, context):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    
    # 🔥 ROUTING TO MODULES 🔥
    
    # 1. Bet Logic (bet.py)
    if data.startswith(("set_", "clk_", "cash_", "close_", "noop_")):
        await bet.bet_callback(update, context)
        return

    # 2. Medical Revive (pay.py)
    if data.startswith("revive_"):
        await pay.revive_callback(update, context)
        return

    # 3. Register (Local)
    if data.startswith("reg_start_"):
        target_id = int(data.split("_")[2])
        if uid != target_id: return await q.answer("Not for you!", show_alert=True)
        if register_user(uid, q.from_user.first_name): await q.edit_message_text("✅ Registered!")
        else: await q.answer("Already registered!")
        return

    # 4. Shop (Local)
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

# --- MESSAGE HANDLER ---
async def handle_message(update, context):
    user = update.effective_user
    chat = update.effective_chat
    if not update.message or not update.message.text: return
    text = update.message.text

    if chat.type in ["group", "supergroup"]:
        update_group_activity(chat.id, chat.title)

    should_reply = False
    if chat.type == "private":
        should_reply = True
    elif chat.type in ["group", "supergroup"]:
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            should_reply = True
        elif "yuki" in text.lower():
            should_reply = True
        elif context.bot.username in text:
            should_reply = True

    if should_reply:
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        ai_reply = get_yuki_response(user.id, text, user.first_name)
        await update.message.reply_text(ai_reply, quote=True)

# --- MAIN ---
def main():
    keep_alive()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", help.help_command))
    
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("redeem", redeem_code))
    app.add_handler(CommandHandler("shop", shop_menu))
    
    # 🔥 Bet Command (From bet.py)
    app.add_handler(CommandHandler("bet", bet.bet_menu))
    
    # 🔥 Bank
    app.add_handler(CommandHandler("bank", bank.bank_info))
    app.add_handler(CommandHandler("deposit", bank.deposit))
    app.add_handler(CommandHandler("withdraw", bank.withdraw))
    app.add_handler(CommandHandler("loan", bank.take_loan))
    app.add_handler(CommandHandler("payloan", bank.repay_loan))
    
    # 🔥 Market
    app.add_handler(CommandHandler("ranking", group.ranking))
    app.add_handler(CommandHandler("market", group.market_info))
    app.add_handler(CommandHandler("invest", group.invest))
    app.add_handler(CommandHandler("sell", group.sell_shares))
    app.add_handler(CommandHandler("top", leaderboard.user_leaderboard))
    
    # 🔥 Crime
    app.add_handler(CommandHandler("pay", pay.pay_user))
    app.add_handler(CommandHandler("rob", pay.rob_user))
    app.add_handler(CommandHandler("kill", pay.kill_user))
    app.add_handler(CommandHandler("protect", pay.protect_user))
    app.add_handler(CommandHandler("alive", pay.check_status))
    
    # 🔥 Admin
    app.add_handler(CommandHandler("eco", admin.economy_toggle))
    app.add_handler(CommandHandler("reset", admin.reset_menu))
    app.add_handler(CommandHandler("cast", admin.broadcast))
    app.add_handler(CommandHandler("code", admin.create_code))
    app.add_handler(CommandHandler("add", admin.add_money))
    app.add_handler(CommandHandler("addkey", admin.add_key_cmd))
    app.add_handler(CommandHandler("delkey", admin.remove_key_cmd))
    app.add_handler(CommandHandler("keys", admin.list_keys_cmd))
    
    app.add_handler(CallbackQueryHandler(admin.reset_callback, pattern="^confirm_wipe$|^cancel_wipe$"))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_join_reward))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 BOT STARTED SUCCESSFULLY!")
    app.run_polling()

if __name__ == "__main__":
    main()
    
