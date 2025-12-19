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

# --- COMMAND: /bet ---
async def bet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Register Check
    if not check_registered(user.id):
        kb = [[InlineKeyboardButton("📝 Register", callback_data=f"reg_start_{user.id}")]]
        await update.message.reply_text(f"🛑 **Register First!**", reply_markup=InlineKeyboardMarkup(kb), quote=True)
        return

    # 🔥 FIX: Group me crash nahi hoga ab
    try: await update.message.delete()
    except: pass 
    
    # 2. Argument Check
    try: bet_amount = int(context.args[0])
    except: 
        await update.message.reply_text("⚠️ **Format:** `/bet 100`", parse_mode=ParseMode.MARKDOWN, quote=True)
        return
        
    # 3. Balance Check
    if get_balance(user.id) < bet_amount: 
        await update.message.reply_text("❌ **Low Balance!**", quote=True)
        return
    
    if bet_amount < 10:
        await update.message.reply_text("❌ Minimum Bet ₹10 hai!", quote=True)
        return

    # 4. Menu Logic
    kb = [
        [InlineKeyboardButton("🟢 1 Bomb", callback_data=f"set_1_{bet_amount}_{user.id}"), InlineKeyboardButton("🟡 3 Bombs", callback_data=f"set_3_{bet_amount}_{user.id}")],
        [InlineKeyboardButton("🔴 5 Bombs", callback_data=f"set_5_{bet_amount}_{user.id}"), InlineKeyboardButton("💀 10 Bombs", callback_data=f"set_10_{bet_amount}_{user.id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"close_{user.id}")]
    ]
    
    # Quote=True taaki user ko tag kare
    await update.message.reply_text(
        f"🎮 **Game Setup ({user.first_name})**\n"
        f"💰 Bet Amount: ₹{bet_amount}\n"
        f"💣 Select Difficulty 👇", 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode=ParseMode.MARKDOWN,
        quote=True
    )

# --- CALLBACK HANDLER (Game Logic) ---
async def bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    parts = data.split("_")
    act = parts[0]

    # --- 1. GAME SETUP (Set Bombs) ---
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
        for i in random.sample(range(16), mines): grid[i] = 1 # 1 = Bomb
        
        active_games[f"{owner}"] = {"grid": grid, "rev": [], "bet": bet, "mines": mines}
        
        # Grid Buttons
        kb = []
        for r in range(4):
            row = []
            for c in range(4): row.append(InlineKeyboardButton("🟦", callback_data=f"clk_{r*4+c}_{owner}"))
            kb.append(row)
            
        await q.edit_message_text(f"💣 Mines: {mines} | Bet: ₹{bet}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # --- 2. GAME CLICK (Play) ---
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

        # BOMB LOGIC
        if game["grid"][idx] == 1:
            del active_games[f"{owner}"]
            await q.edit_message_text(f"💥 **BOOM!** Lost ₹{game['bet']}", parse_mode=ParseMode.MARKDOWN)
        
        # SAFE LOGIC
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
                
                await q.edit_message_text(f"💎 Safe! Win: ₹{win_now}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # --- 3. CASHOUT ---
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
        del active_games[f"{owner}"]
        
        await q.edit_message_text(f"💰 **Cashed Out: ₹{win}**", parse_mode=ParseMode.MARKDOWN)

    # --- 4. CLOSE / NOOP ---
    if act == "close": 
        owner = int(parts[1])
        if uid != owner: await q.answer("Tum close nahi kar sakte!"); return
        await q.message.delete()
        
    if act == "noop": await q.answer("Ye khul chuka hai!", show_alert=False)
        
