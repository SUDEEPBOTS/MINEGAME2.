import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# IMPORTS
from config import TELEGRAM_TOKEN, GRID_SIZE, DELETE_TIMER
from database import users_col, codes_col, get_user, update_balance, get_balance, check_registered, register_user, update_group_activity
from ai_chat import get_yuki_response
# ALL MODULES IMPORTED
import admin, start, help, group, leaderboard, pay, bank 

# --- FLASK SERVER (FOR UPTIME) ---
app = Flask('')

@app.route('/')
def home(): return "I am Alive! 24/7"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): t = Thread(target=run); t.start()

# VARS
active_games = {} 
SHOP_ITEMS = {
    "vip":   {"name": "👑 VIP", "price": 10000},
    "god":   {"name": "⚡ God", "price": 50000},
    "rich":  {"name": "💸 Rich", "price": 100000}
}
BOMB_CONFIG = {
    1:  [1.01, 1.08, 1.15, 1.25, 1.40, 1.55, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0], 
    3:  [1.10, 1.25, 1.45, 1.75, 2.15, 2.65, 3.30, 4.2, 5.5, 7.5, 10.0, 15.0], 
    5:  [1.30, 1.65, 2.20, 3.00, 4.20, 6.00, 9.00, 14.0, 22.0, 35.0, 50.0],    
    10: [2.50, 4.50, 9.00, 18.0, 40.0, 80.0]                                   
}

# --- FUNCTIONS ---
async def delete_job(context):
    try: await context.bot.delete_message(context.job.chat_id, context.job.data)
    except: pass

async def ensure_registered(update, context):
    user = update.effective_user
    if not check_registered(user.id):
        kb = [[InlineKeyboardButton("📝 Register", callback_data=f"reg_start_{user.id}")]]
        # Quote=True taaki group me pata chale kiske liye msg hai
        await update.message.reply_text(f"🛑 **{user.first_name}, Register First!**\nGet ₹500 Bonus.", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN, quote=True)
        return False
    return True

# --- GROUP REWARD LOGIC ---
async def group_join_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jab Bot ko Group me add kiya jaye tab Reward dega"""
    if not update.message.new_chat_members: return

    for member in update.message.new_chat_members:
        # Check agar new member khud Bot hai
        if member.id == context.bot.id:
            adder = update.message.from_user
            
            # Reward: ₹1000
            update_balance(adder.id, 1000)
            
            await update.message.reply_text(
                f"🎉 **Thanks {adder.first_name}!**\n"
                f"Mujhe apne Group me add karne ke liye.\n"
                f"💸 **Reward:** ₹1000 added to your wallet!",
                parse_mode=ParseMode.MARKDOWN
            )

# --- COMMANDS ---

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bal = get_balance(user.id)
    await update.message.reply_text(f"💳 **{user.first_name}'s Balance:** ₹{bal}", parse_mode=ParseMode.MARKDOWN, quote=True)

async def redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_registered(update, context): return
    user = update.effective_user
    
    if not context.args: 
        msg = await update.message.reply_text("⚠️ Usage: `/redeem <code>`", quote=True)
        context.job_queue.run_once(delete_job, 5, chat_id=msg.chat_id, data=msg.message_id)
        return

    code_name = context.args[0].strip() # Spaces fix

    code_data = codes_col.find_one({"code": code_name})
    if not code_data: return await update.message.reply_text("❌ Invalid Code! (Spelling Check Karo)", quote=True)
    
    if user.id in code_data.get("redeemed_by", []): return await update.message.reply_text("⚠️ You already redeemed this code!", quote=True)
    
    if len(code_data.get("redeemed_by", [])) >= code_data.get("limit", 0): return await update.message.reply_text("❌ Code Limit Reached (Expired)!", quote=True)
    
    amount = code_data["amount"]
    update_balance(user.id, amount)
    codes_col.update_one({"code": code_name}, {"$push": {"redeemed_by": user.id}})
    
    await update.message.reply_text(f"🎉 **Success!**\nAdded: ₹{amount}\nNew Balance: ₹{get_balance(user.id)}", parse_mode=ParseMode.MARKDOWN, quote=True)

async def bet_menu(update, context):
    if not await ensure_registered(update, context): return
    
    # Try delete (Groups me aksar fail hota hai isliye pass)
    try: await update.message.delete()
    except: pass 
    
    try: bet = int(context.args[0])
    except: 
        msg = await update.message.reply_text("⚠️ **Format:** `/bet 100`", parse_mode=ParseMode.MARKDOWN, quote=True)
        context.job_queue.run_once(delete_job, 5, chat_id=msg.chat_id, data=msg.message_id)
        return
        
    uid = update.effective_user.id
    if get_balance(uid) < bet: 
        msg = await update.message.reply_text("❌ **Low Balance!**\nPaisa kama ke aao.", quote=True)
        context.job_queue.run_once(delete_job, 5, chat_id=msg.chat_id, data=msg.message_id)
        return
    
    kb = [
        [InlineKeyboardButton("🟢 1 Bomb", callback_data=f"set_1_{bet}_{uid}"), InlineKeyboardButton("🟡 3 Bombs", callback_data=f"set_3_{bet}_{uid}")],
        [InlineKeyboardButton("🔴 5 Bombs", callback_data=f"set_5_{bet}_{uid}"), InlineKeyboardButton("💀 10 Bombs", callback_data=f"set_10_{bet}_{uid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"close_{uid}")]
    ]
    # Quote=True se group me reply sahi jayega
    await update.message.reply_text(f"🎮 **Game Setup ({update.effective_user.first_name})**\nBet: ₹{bet}\nSelect Difficulty 👇", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN, quote=True)

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
    
    # 🔥 MEDICAL REVIVE (Important Added Here)
    if data.startswith("revive_"):
        await pay.revive_callback(update, context)
        return

    # REGISTER BUTTON
    if data.startswith("reg_start_"):
        target_id = int(data.split("_")[2])
        if uid != target_id: 
            await q.answer("Ye button tumhare liye nahi hai! 😠", show_alert=True)
            return
        if register_user(uid, q.from_user.first_name): 
            await q.edit_message_text("✅ **Registered!**\nBonus ₹500 Added.", parse_mode=ParseMode.MARKDOWN)
        else: 
            await q.answer("Already registered!")
        return

    parts = data.split("_")
    act = parts[0]
    
    # SHOP BUY
    if act == "buy":
        target_id = int(parts[2])
        if uid != target_id:
            await q.answer("Apna Shop Kholo! 🛒", show_alert=True)
            return 
        item = SHOP_ITEMS.get(parts[1])
        if get_balance(uid) < item["price"]: 
            await q.answer("Paisa nahi hai! ❌", show_alert=True)
            return
        update_balance(uid, -item["price"])
        users_col.update_one({"_id": uid}, {"$push": {"titles": item["name"]}})
        await q.answer(f"✅ Bought {item['name']}!")
        await q.message.delete()
        return

    # GAME START
    if act == "set":
        owner = int(parts[3])
        if uid != owner:
            await q.answer("Ye game tumhara nahi hai! 🚫", show_alert=True)
            return
        mines = int(parts[1]); bet = int(parts[2])
        if get_balance(owner) < bet: 
            await q.answer("Balance khatam ho gaya! 📉", show_alert=True)
            await q.message.delete()
            return
        update_balance(owner, -bet)
        grid = [0]*(GRID_SIZE**2)
        for i in random.sample(range(16), mines): grid[i] = 1
        active_games[f"{owner}"] = {"grid": grid, "rev": [], "bet": bet, "mines": mines}
        kb = []
        for r in range(4):
            row = []
            for c in range(4): row.append(InlineKeyboardButton("🟦", callback_data=f"clk_{r*4+c}_{owner}"))
            kb.append(row)
        await q.edit_message_text(f"💣 Mines: {mines} | Bet: ₹{bet}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # GAME PLAY
    if act == "clk":
        owner = int(parts[2])
        if uid != owner:
            await q.answer("Apna game khelo bhai! 😒", show_alert=True)
            return
        game = active_games.get(f"{owner}")
        if not game: 
            await q.answer("Game Expired / Error ❌", show_alert=True)
            await q.message.delete()
            return
        idx = int(parts[1])
        
        if idx in game["rev"]:
            await q.answer("Already Open Hai! 👀", show_alert=False)
            return

        if game["grid"][idx] == 1:
            del active_games[f"{owner}"]
            await q.edit_message_text(f"💥 **BOOM!** Lost ₹{game['bet']}", parse_mode=ParseMode.MARKDOWN)
            context.job_queue.run_once(delete_job, DELETE_TIMER, chat_id=q.message.chat_id, data=q.message.message_id)
        else:
            game["rev"].append(idx)
            mults = BOMB_CONFIG[game["mines"]]
            if len(game["rev"]) == (16 - game["mines"]):
                win = int(game["bet"] * mults[-1])
                update_balance(owner, win)
                del active_games[f"{owner}"]
                await q.edit_message_text(f"👑 **JACKPOT! WON ₹{win}**", parse_mode=ParseMode.MARKDOWN)
            else:
                kb = []
                for r in range(4):
                    row = []
                    for c in range(4):
                        i = r*4+c
                        if i in game["rev"]:
                            txt = "💎"; cb = f"noop_{i}"
                        else:
                            txt = "🟦"; cb = f"clk_{i}_{owner}"
                        row.append(InlineKeyboardButton(txt, callback_data=cb))
                    kb.append(row)
                win_now = int(game["bet"] * mults[len(game["rev"])-1])
                kb.append([InlineKeyboardButton(f"💰 Cashout ₹{win_now}", callback_data=f"cash_{owner}")])
                await q.edit_message_text(f"💎 Safe! Current Win: ₹{win_now}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # CASHOUT
    if act == "cash":
        owner = int(parts[1])
        if uid != owner:
            await q.answer("Haath mat lagana! 😡", show_alert=True)
            return
        game = active_games.get(f"{owner}")
        if not game:
            await q.answer("Game Khatam!", show_alert=True)
            await q.message.delete()
            return
        mults = BOMB_CONFIG[game["mines"]]
        win = int(game["bet"] * mults[len(game["rev"])-1])
        update_balance(owner, win)
        del active_games[f"{owner}"]
        await q.edit_message_text(f"💰 **Cashed Out: ₹{win}**", parse_mode=ParseMode.MARKDOWN)
        context.job_queue.run_once(delete_job, DELETE_TIMER, chat_id=q.message.chat_id, data=q.message.message_id)

    if act == "close": 
        owner = int(parts[1])
        if uid != owner:
            await q.answer("Tum close nahi kar sakte!", show_alert=True)
            return
        await q.message.delete()
        
    if act == "noop": await q.answer("Ye khul chuka hai!", show_alert=False)

# --- MESSAGE HANDLER ---
async def handle_message(update, context):
    user = update.effective_user
    chat = update.effective_chat
    if not update.message or not update.message.text: return
    text = update.message.text

    # Group Activity Track
    if chat.type in ["group", "supergroup"]:
        update_group_activity(chat.id, chat.title)

    # Yuki Chat Logic
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
    
    # Basic
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", help.help_command))
    
    # Game & Eco
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("bet", bet_menu))
    app.add_handler(CommandHandler("shop", shop_menu))
    app.add_handler(CommandHandler("redeem", redeem_code))
    
    # BANK
    app.add_handler(CommandHandler("bank", bank.bank_info))
    app.add_handler(CommandHandler("deposit", bank.deposit))
    app.add_handler(CommandHandler("withdraw", bank.withdraw))
    app.add_handler(CommandHandler("loan", bank.take_loan))
    app.add_handler(CommandHandler("payloan", bank.repay_loan))
    
    # Market
    app.add_handler(CommandHandler("ranking", group.ranking))
    app.add_handler(CommandHandler("market", group.market_info))
    app.add_handler(CommandHandler("invest", group.invest))
    app.add_handler(CommandHandler("sell", group.sell_shares))
    app.add_handler(CommandHandler("top", leaderboard.user_leaderboard))
    
    # Pay & Crime
    app.add_handler(CommandHandler("pay", pay.pay_user))
    app.add_handler(CommandHandler("rob", pay.rob_user))
    app.add_handler(CommandHandler("kill", pay.kill_user))
    app.add_handler(CommandHandler("protect", pay.protect_user))
    app.add_handler(CommandHandler("alive", pay.check_status))
    
    # Reset & Admin
    app.add_handler(CommandHandler("eco", admin.economy_toggle))
    app.add_handler(CommandHandler("reset", admin.reset_menu))
    
    # Admin Utils
    app.add_handler(CommandHandler("cast", admin.broadcast))
    app.add_handler(CommandHandler("code", admin.create_code))
    app.add_handler(CommandHandler("add", admin.add_money))
    
    app.add_handler(CommandHandler("addkey", admin.add_key_cmd))
    app.add_handler(CommandHandler("delkey", admin.remove_key_cmd))
    app.add_handler(CommandHandler("keys", admin.list_keys_cmd))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(admin.reset_callback, pattern="^confirm_wipe$|^cancel_wipe$"))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # 🔥 GROUP ADD HANDLER (Paisa milega)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_join_reward))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 BOT STARTED SUCCESSFULLY!")
    app.run_polling()

if __name__ == "__main__":
    main()
            
