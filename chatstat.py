from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import get_top_chatters, get_total_messages

# --- PROGRESS BAR GENERATOR ---
def make_bar(count, max_count):
    """
    Creates a bar like: ▰▰▰▰▱▱▱
    """
    if max_count == 0: return "▱▱▱▱▱▱▱▱▱▱"
    
    # Calculate percentage (10 blocks max)
    percentage = count / max_count
    filled = int(percentage * 10) 
    
    # Safety fix (10 se zyada na ho)
    if filled > 10: filled = 10
    
    empty = 10 - filled
    return "▰" * filled + "▱" * empty

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🔥 Debug Print
    print("DEBUG: /crank triggered") 

    if update.callback_query:
        chat_id = update.effective_chat.id
    else:
        chat_id = update.effective_chat.id

    # Default Mode: Overall
    mode = "overall"
    if context.args and context.args[0] in ["today", "week"]:
        mode = context.args[0]

    await send_rank_message(chat_id, mode, update, context)

async def send_rank_message(chat_id, mode, update, context):
    data = get_top_chatters(chat_id, mode)
    total = get_total_messages(chat_id)
    
    # Titles
    title_map = {
        "overall": "☁️ OVERALL LEADERBOARD",
        "today": "☀️ TODAY'S TOP CHATTERS",
        "week": "🗓 WEEKLY TOP CHATTERS"
    }

    # Header
    text = f"📈 **{title_map[mode]}**\n\n"
    
    if not data:
        text += "❌ **No data found yet!**\nStart chatting to appear here."
    else:
        # Sabse top bande ka score (Bar calculate karne ke liye)
        max_count = data[0].get(mode, 1)

        for i, user in enumerate(data, 1):
            name = user.get("name", "Unknown")
            count = user.get(mode, 0)
            bar = make_bar(count, max_count)
            
            # Icons Logic
            if i == 1: icon = "🥇"
            elif i == 2: icon = "🥈"
            elif i == 3: icon = "🥉"
            else: icon = f"{i}."
            
            # 🔥 FINAL FORMAT 🔥
            text += f"{icon} 👤 **{name}**\n"
            text += f"   └ {bar} • `{count}`\n\n"
    
    text += f"📨 **Total Group Messages:** `{total}`"
    
    # Buttons
    kb = [
        [
            InlineKeyboardButton("Overall", callback_data="rank_overall"),
            InlineKeyboardButton("Today", callback_data="rank_today"),
            InlineKeyboardButton("Week", callback_data="rank_week")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_rank")]
    ]
    
    # Send or Edit Logic
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass # Agar content same ho to error ignore karo
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )

# --- CALLBACK HANDLER (FIXED) ---
async def rank_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    
    # 🔥 FIXED CLOSE LOGIC
    if data == "close_rank":
        try:
            await q.answer("Closing...") # Animation stop karega
            await q.message.delete()
        except Exception as e:
            print(f"Error deleting message: {e}")
        return

    if data.startswith("rank_"):
        try:
            await q.answer() # Animation stop
        except: pass
        
        mode = data.split("_")[1]
        await send_rank_message(update.effective_chat.id, mode, update, context)
