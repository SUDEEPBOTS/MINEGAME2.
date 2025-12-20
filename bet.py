import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from config import GRID_SIZE
from database import get_balance, update_balance, check_registered

# --- GAME CONFIGS ---
active_games = {} 

BOMB_CONFIG = {
    1:  [1.01, 1.08, 1.15, 1.25, 1.40, 1.55, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0], 
    3:  [1.10, 1.25, 1.45, 1.75, 2.15, 2.65, 3.30, 4.2, 5.5, 7.5, 10.0, 15.0], 
    5:  [1.30, 1.65, 2.20, 3.00, 4.20, 6.00, 9.00, 14.0, 22.0, 35.0, 50.0],    
    10: [2.50, 4.50, 9.00, 18.0, 40.0, 80.0]                                   
}

# --- HELPER: AUTO DELETE ---
async def delete_msg(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(context.job.chat_id, context.job.data)
    except: pass

# --- COMMAND: /bet ---
async def bet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # 1. DELETE USER COMMAND (Safayi ke liye)
    try: await update.message.delete()
    except: pass 

    # 2. Register Check
    if not check_registered(user.id):
        kb = [[InlineKeyboardButton("📝 Register", callback_data=f"reg_start_{user.id}")]]
        # Hum 'send_message' use karenge taaki deleted msg pe reply karne ka error na aaye
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🛑 **{user.first_name}, Register First!**", 
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        context.job_queue.run_once(delete_msg, 10, chat_id=chat_id, data=msg.message_id)
        return
    
    # 3. Argument Check
    try: bet_amount = int(context.args[0])
    except: 
        msg = await context.bot.send_message(chat_id=chat_id, text="⚠️ **Format:** `/bet 100`", parse_mode=ParseMode.MARKDOWN)
        context.job_queue.run_once(delete_msg, 5, chat_id=chat_id, data=msg.message_id)
        return
        
    # 4. Balance Check
    if get_balance(user.id) < bet_amount: 
        msg = await context.bot.send_message(chat_id=chat_id, text=f"❌ **Low Balance!** {user.first_name}, paisa nahi hai.", parse_mode=ParseMode.MARKDOWN)
        context.job_queue.run_once(delete_msg, 5, chat_id=chat_id, data=msg.message_id)
        return
    
    if bet_amount < 10:
        msg = await context.bot.send_message(chat_id=chat_id, text="❌ Minimum Bet ₹10 hai!")
        context.job_queue.run_once(delete_msg, 5, chat_id=chat_id, data=msg.message_id)
        return

    # 5. Menu Logic
    kb = [
        [InlineKeyboardButton("🟢 1 Bomb", callback_data=f"set_1_{bet_amount}_{user.id}"), InlineKeyboardButton("🟡 3 Bombs", callback_data=f"set_3_{bet_amount}_{user.id}")],
        [InlineKeyboardButton("🔴 5 Bombs", callback_data=f"set_5_{bet_amount}_{user.id}"), InlineKeyboardButton("💀 10 Bombs", callback_data=f"set_10_{bet_amount}_{user.id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"close_{user.id}")]
    ]
    
    # 🔥 New formatted message
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎲 **NEW BET STARTED**\n"
            f"👤 **Player:** {user.first_name}\n"
            f"💵 **Amount:** ₹{bet_amount}\n"
            f"💣 **Choose Difficulty:** 👇"
        ),
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode=ParseMode.MARKDOWN
    )

# --- CALLBACK HANDLER ---
async def bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    parts = data.split("_")
    act = parts[0]

    # --- REBET (PLAY AGAIN) ---
    if act == "rebet":
        bet_amount = int(parts[1])
        owner = int(parts[2])

        if uid != owner:
            await q.answer("Ye button tumhare liye nahi hai!", show_alert=True)
            return

        if get_balance(owner) < bet_amount:
            await q.answer("Balance khatam ho gaya!", show_alert=True)
            return

        kb = [
            [InlineKeyboardButton("🟢 1 Bomb", callback_data=f"set_1_{bet_amount}_{owner}"), InlineKeyboardButton("🟡 3 Bombs", callback_data=f"set_3_{bet_amount}_{owner}")],
            [InlineKeyboardButton("🔴 5 Bombs", callback_data=f"set_5_{bet_amount}_{owner}"), InlineKeyboardButton("💀 10 Bombs", callback_data=f"set_10_{bet_amount}_{owner}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"close_{owner}")]
        ]
        
        await q.edit_message_text(
            text=(
                f"🎲 **NEW BET STARTED**\n"
                f"👤 **Player:** {q.from_user.first_name}\n"
                f"💵 **Amount:** ₹{bet_amount}\n"
                f"💣 **Choose Difficulty:** 👇"
            ),
            reply_markup=InlineKeyboardMarkup(kb), 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # --- GAME SETUP (Set Difficulty) ---
    if act == "set":
        owner = int(parts[3])
        if uid != owner:
            await q.answer("Ye game tumhara nahi hai!", show_alert=True)
            return
            
        mines = int(parts[1]); bet = int(parts[2])
        
        if get_balance(owner) < bet: 
            await q.answer("Balance khatam ho gaya!", show_alert=True)
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
            
        # 🔥 Updated Game Info Message
        await q.edit_message_text(
            text=(
                f"🎮 **GAME STARTED**\n"
                f"👤 **Player:** {q.from_user.first_name}\n"
                f"💰 **Bet:** ₹{bet}\n"
                f"💣 **Mines:** {mines}\n"
                f"➖➖➖➖➖➖➖➖"
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # --- GAME CLICK ---
    if act == "clk":
        owner = int(parts[2])
        if uid != owner:
            await q.answer("Apna game khelo!", show_alert=True)
            return
            
        game = active_games.get(f"{owner}")
        if not game: 
            await q.answer("Game Expired ❌", show_alert=True)
            await q.message.delete()
            return
            
        idx = int(parts[1])
        
        if idx in game["rev"]:
            await q.answer("Already Open Hai!", show_alert=False)
            return

        # 🔥 BOMB LOGIC (LOSS) 🔥
        if game["grid"][idx] == 1:
            del active_games[f"{owner}"]
            
            # Reveal All
            kb = []
            for r in range(4):
                row = []
                for c in range(4):
                    i = r * 4 + c
                    if i == idx: txt = "💥"
                    elif game["grid"][i] == 1: txt = "💣"
                    else: txt = "💎"
                    row.append(InlineKeyboardButton(txt, callback_data=f"noop_{i}"))
                kb.append(row)
            
            kb.append([InlineKeyboardButton("🔄 New Game", callback_data=f"rebet_{game['bet']}_{owner}")])
            
            await q.edit_message_text(
                text=(
                    f"💥 **BOOM! GAME OVER**\n"
                    f"👤 **Player:** {update.effective_user.first_name}\n"
                    f"💣 **Mines:** {game['mines']}\n"
                    f"📉 **Lost:** ₹{game['bet']}"
                ),
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        
        # SAFE LOGIC
        else:
            game["rev"].append(idx)
            mults = BOMB_CONFIG[game["mines"]]
            
            # JACKPOT WIN
            if len(game["rev"]) == (16 - game["mines"]):
                win = int(game["bet"] * mults[-1])
                update_balance(owner, win)
                del active_games[f"{owner}"]
                
                # Reveal
                kb = []
                for r in range(4):
                    row = []
                    for c in range(4):
                        i = r * 4 + c
                        if game["grid"][i] == 1: txt = "💣"
                        else: txt = "💎"
                        row.append(InlineKeyboardButton(txt, callback_data=f"noop_{i}"))
                    kb.append(row)
                
                kb.append([InlineKeyboardButton("🔄 New Game", callback_data=f"rebet_{game['bet']}_{owner}")])
                
                await q.edit_message_text(
                    text=(
                        f"👑 **JACKPOT! YOU WON**\n"
                        f"👤 **Player:** {update.effective_user.first_name}\n"
                        f"💣 **Mines:** {game['mines']}\n"
                        f"💰 **Won:** ₹{win}"
                    ),
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # CONTINUE GAME
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
                
                await q.edit_message_text(
                    text=(
                        f"💎 **SAFE! KEEP GOING**\n"
                        f"👤 {update.effective_user.first_name}\n"
                        f"💰 Profit: ₹{win_now}\n"
                        f"💣 Mines: {game['mines']}"
                    ),
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode=ParseMode.MARKDOWN
                )
        return

    # --- CASHOUT ---
    if act == "cash":
        owner = int(parts[1])
        if uid != owner:
            await q.answer("Haath mat lagana!", show_alert=True)
            return
            
        game = active_games.get(f"{owner}")
        if not game:
            await q.answer("Game Khatam!", show_alert=True)
            await q.message.delete()
            return
            
        mults = BOMB_CONFIG[game["mines"]]
        win = int(game["bet"] * mults[len(game["rev"])-1])
        
        update_balance(owner, win)
        bet_amount = game['bet']
        del active_games[f"{owner}"]
        
        # Reveal
        kb = []
        for r in range(4):
            row = []
            for c in range(4):
                i = r * 4 + c
                if game["grid"][i] == 1: txt = "💣"
                else: txt = "💎"
                row.append(InlineKeyboardButton(txt, callback_data=f"noop_{i}"))
            kb.append(row)

        kb.append([InlineKeyboardButton("🔄 New Game", callback_data=f"rebet_{bet_amount}_{owner}")])
        
        await q.edit_message_text(
            text=(
                f"💰 **CASHED OUT SUCCESS**\n"
                f"👤 **Player:** {update.effective_user.first_name}\n"
                f"💣 **Mines:** {game['mines']}\n"
                f"💵 **Profit:** ₹{win}"
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

    # --- CLOSE ---
    if act == "close": 
        owner = int(parts[1])
        if uid != owner: await q.answer("Tum close nahi kar sakte!"); return
        await q.message.delete()
        
    if act == "noop": await q.answer("Game Over ho gaya bhai!", show_alert=False)
        
