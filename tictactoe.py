import html
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import update_balance, get_user

# Global Dictionary
ttt_games = {}

# Reward Config
REWARD_AMOUNT = 500  # Amount won for beating the bot or another player

# Winning Combinations
WIN_COMBOS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8], # Rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8], # Cols
    [0, 4, 8], [2, 4, 6]             # Diagonals
]

def to_fancy(text):
    mapping = {'A': 'Λ', 'E': 'Є', 'S': 'δ', 'O': 'σ', 'T': 'ᴛ', 'N': 'ɴ', 'M': 'ᴍ', 'U': 'ᴜ', 'R': 'ʀ', 'D': 'ᴅ', 'C': 'ᴄ', 'P': 'ᴘ', 'G': 'ɢ', 'B': 'ʙ', 'L': 'ʟ', 'W': 'ᴡ', 'K': 'ᴋ', 'J': 'ᴊ', 'Y': 'ʏ', 'I': 'ɪ', 'H': 'ʜ'}
    return "".join(mapping.get(c.upper(), c) for c in text)

# --- BOT LOGIC (DIFFICULTY BASED) ---
def get_bot_move(board, difficulty):
    available = [i for i, x in enumerate(board) if x == " "]
    if not available: return None

    # EASY: Completely Random
    if difficulty == "easy":
        return random.choice(available)

    # MEDIUM: 50% chance to play smart, 50% random
    if difficulty == "medium":
        if random.random() < 0.3:
             return random.choice(available)
        # Else fall through to Hard logic (Smart)

    # HARD: Minimax-Lite (Win > Block > Center > Random)
    # 1. Win now
    for combo in WIN_COMBOS:
        line = [board[i] for i in combo]
        if line.count("O") == 2 and line.count(" ") == 1:
            return combo[line.index(" ")]

    # 2. Block Player
    for combo in WIN_COMBOS:
        line = [board[i] for i in combo]
        if line.count("X") == 2 and line.count(" ") == 1:
            return combo[line.index(" ")]

    # 3. Take Center
    if board[4] == " ": return 4

    # 4. Random
    return random.choice(available)

# --- 1. START COMMAND (/zero) ---
async def start_ttt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    msg = f"""
<blockquote><b>🎮 {to_fancy("TIC TAC TOE")}</b></blockquote>
<blockquote><b>👤 ᴘʟᴀʏᴇʀ :</b> {html.escape(user.first_name)}
<b>⚔️ ᴄʜᴏᴏsᴇ ᴍᴏᴅᴇ :</b> 👇</blockquote>
"""
    kb = [
        [InlineKeyboardButton("👥 1 vs 1 (PvP)", callback_data=f"ttt_init_pvp_{user.id}")],
        [InlineKeyboardButton("🤖 Play with Bot", callback_data=f"ttt_diff_ask_{user.id}")],
        [InlineKeyboardButton("❌ Close", callback_data="ttt_close")]
    ]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# --- 2. GAME LOGIC ---
def check_winner(board):
    for combo in WIN_COMBOS:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] and board[combo[0]] != " ":
            return board[combo[0]]
    if " " not in board:
        return "Draw"
    return None

def get_board_markup(game_id):
    game = ttt_games[game_id]
    board = game["board"]
    kb = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            text = board[idx]
            if text == " ": text = "⬜"
            elif text == "X": text = "❌"
            elif text == "O": text = "⭕"
            row.append(InlineKeyboardButton(text, callback_data=f"ttt_move_{idx}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("❌ End Game", callback_data="ttt_close")])
    return InlineKeyboardMarkup(kb)

# --- 3. CALLBACK HANDLER ---
async def ttt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user = q.from_user
    msg_id = q.message.message_id
    
    # A. CLOSE
    if data == "ttt_close":
        if msg_id in ttt_games: del ttt_games[msg_id]
        await q.message.delete()
        return

    # B. DIFFICULTY SELECTION
    if data.startswith("ttt_diff_ask_"):
        user_id = int(data.split("_")[3])
        if user.id != user_id:
             await q.answer("Not your game!", show_alert=True)
             return
             
        kb = [
            [InlineKeyboardButton("🟢 Easy", callback_data=f"ttt_init_bot_easy_{user_id}")],
            [InlineKeyboardButton("🟡 Medium", callback_data=f"ttt_init_bot_medium_{user_id}")],
            [InlineKeyboardButton("🔴 Hard", callback_data=f"ttt_init_bot_hard_{user_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"ttt_back_start_{user_id}")]
        ]
        await q.edit_message_text(
            f"<blockquote><b>🤖 {to_fancy('SELECT DIFFICULTY')}</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        return

    # Back to Start
    if data.startswith("ttt_back_start_"):
        # We can't easily go back to start without context arguments, so we just restart the menu logic locally
        # Simplest way is to just call the initial menu logic again manually or delete/resend.
        # Here we just show the initial menu text again.
        await q.edit_message_text(
            f"<blockquote><b>🎮 {to_fancy('TIC TAC TOE')}</b></blockquote>\n<blockquote><b>👤 ᴘʟᴀʏᴇʀ :</b> {html.escape(user.first_name)}\n<b>⚔️ ᴄʜᴏᴏsᴇ ᴍᴏᴅᴇ :</b> 👇</blockquote>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 1 vs 1 (PvP)", callback_data=f"ttt_init_pvp_{user.id}")],
                [InlineKeyboardButton("🤖 Play with Bot", callback_data=f"ttt_diff_ask_{user.id}")],
                [InlineKeyboardButton("❌ Close", callback_data="ttt_close")]
            ]),
            parse_mode=ParseMode.HTML
        )
        return

    # C. INITIALIZE GAME
    if data.startswith("ttt_init_"):
        parts = data.split("_")
        mode = parts[2] # 'pvp' or 'bot'
        
        if mode == "bot":
            difficulty = parts[3] # easy/medium/hard
            p1_id = int(parts[4])
        else:
            difficulty = None
            p1_id = int(parts[3])
        
        game_data = {
            "board": [" "] * 9,
            "turn": "X",
            "p1": p1_id,
            "p2": None, 
            "p1_name": user.first_name,
            "p2_name": "Waiting...",
            "mode": mode,
            "diff": difficulty
        }

        if mode == "bot":
            game_data["p2"] = 0 
            game_data["p2_name"] = f"Mimi ({difficulty.title()})"

        ttt_games[msg_id] = game_data
        
        status_text = f"❌ <b>Turn:</b> {html.escape(user.first_name)}"
        
        await q.edit_message_text(
            f"<blockquote><b>🎮 {to_fancy('GAME STARTED')}</b></blockquote>\n<blockquote>{status_text}</blockquote>",
            reply_markup=get_board_markup(msg_id),
            parse_mode=ParseMode.HTML
        )
        return

    # D. PLAYER MOVE
    if data.startswith("ttt_move_"):
        if msg_id not in ttt_games:
            await q.answer("❌ Game Expired!", show_alert=True)
            try: await q.message.delete()
            except: pass
            return
            
        game = ttt_games[msg_id]
        idx = int(data.split("_")[2])
        
        # --- PvP ASSIGN ---
        if game["mode"] == "pvp":
            if game["p2"] is None:
                if user.id == game["p1"]:
                    await q.answer("⚠️ Wait for opponent!", show_alert=True)
                    return
                game["p2"] = user.id
                game["p2_name"] = user.first_name
        
        # --- TURN CHECK ---
        is_p1 = (user.id == game["p1"])
        is_p2 = (user.id == game["p2"])
        
        if game["turn"] == "X" and not is_p1:
            await q.answer("❌ Not your turn!", show_alert=True)
            return
        if game["turn"] == "O":
            if game["mode"] == "bot":
                 await q.answer("❌ Bot is moving!", show_alert=True)
                 return
            if not is_p2:
                await q.answer("❌ Not your turn!", show_alert=True)
                return
        
        if game["board"][idx] != " ":
            await q.answer("⚠️ Taken!", show_alert=True)
            return
            
        # --- MOVE ---
        game["board"][idx] = game["turn"]
        
        # CHECK WIN (Player)
        winner = check_winner(game["board"])
        if winner:
            await end_game(q, game, winner, msg_id)
            return

        # SWITCH
        game["turn"] = "O" if game["turn"] == "X" else "X"
        
        # --- BOT MOVE ---
        if game["mode"] == "bot" and game["turn"] == "O":
            # Update UI first
            await q.edit_message_text(
                f"<blockquote><b>🎮 {to_fancy('GAME ON')}</b></blockquote>\n<blockquote>🤖 <b>Turn:</b> Mimi is thinking...</blockquote>",
                reply_markup=get_board_markup(msg_id),
                parse_mode=ParseMode.HTML
            )
            
            # Bot Move
            bot_idx = get_bot_move(game["board"], game["diff"])
            
            if bot_idx is not None:
                game["board"][bot_idx] = "O"
                
                # Check Win (Bot)
                winner = check_winner(game["board"])
                if winner:
                    await end_game(q, game, winner, msg_id)
                    return
                
                game["turn"] = "X"
        
        # NEXT TURN UI
        next_player = game["p1_name"] if game["turn"] == "X" else game["p2_name"]
        
        await q.edit_message_text(
            f"<blockquote><b>🎮 {to_fancy('GAME ON')}</b></blockquote>\n<blockquote>{( '❌' if game['turn']=='X' else '⭕' )} <b>Turn:</b> {html.escape(next_player)}</blockquote>",
            reply_markup=get_board_markup(msg_id),
            parse_mode=ParseMode.HTML
        )

# --- HELPER: END GAME & REWARD ---
async def end_game(q, game, winner, msg_id):
    if winner == "Draw":
        txt = f"<blockquote><b>🤝 {to_fancy('GAME DRAW')}!</b></blockquote>\n<blockquote>Nobody won.</blockquote>"
    else:
        # Determine Winner ID & Name
        if winner == "X":
            w_id = game["p1"]
            w_name = game["p1_name"]
        else:
            w_id = game["p2"]
            w_name = game["p2_name"]
            
        # Give Reward (If winner is a real user)
        if w_id != 0:
            update_balance(w_id, REWARD_AMOUNT)
            prize_txt = f"\n💰 <b>Won:</b> ₹{REWARD_AMOUNT}"
        else:
            prize_txt = "\n🤖 <b>Bot Won!</b> Better luck next time."

        txt = f"<blockquote><b>👑 {to_fancy('WINNER')} : {html.escape(w_name)}</b></blockquote>\n<blockquote>🎉 Congratulations!{prize_txt}</blockquote>"
    
    if msg_id in ttt_games: del ttt_games[msg_id]
    await q.edit_message_text(txt, parse_mode=ParseMode.HTML)
