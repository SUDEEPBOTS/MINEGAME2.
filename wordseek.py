from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import ContextTypes
import random
import asyncio

# Imports
from database import update_wordseek_score, get_wordseek_leaderboard

# GAME STATE
active_games = {}

# --- 🔥 VALID WORDS LIST (Updated Dictionary) ---
VALID_GUESSES = {
    "APPLE", "TIGER", "BREAD", "CHAIR", "SMILE", "BEACH", "DREAM", "LIGHT", "HEART", "WATCH",
    "WATER", "MUSIC", "MONEY", "HOUSE", "WORLD", "PHONE", "TABLE", "PAPER", "RIVER", "NIGHT",
    "HAPPY", "GREEN", "QUICK", "ZEBRA", "CLOUD", "SNAKE", "GHOST", "ROBOT", "PIZZA", "QUEEN",
    "TRAIN", "FRUIT", "GRAPE", "LEMON", "MELON", "BERRY", "PEACH", "MANGO", "ONION", "SALAD",
    "SUGAR", "CANDY", "JUICE", "CREAM", "PARTY", "DANCE", "SONGS", "MOVIE", "ACTOR", "DRAMA",
    "STAGE", "PIANO", "GUITAR", "DRUMS", "FLUTE", "PAINT", "COLOR", "BLACK", "WHITE", "CLOTH",
    "SHIRT", "SHOES", "PANTS", "DRESS", "SKIRT", "SOCKS", "WATCH", "CLOCK", "ALARM", "TIMER",
    "HOURS", "MONTH", "YEARS", "TODAY", "NIGHT", "EARLY", "LATER", "NEVER", "WHERE", "THERE",
    "EVERY", "WHICH", "OTHER", "ABOUT", "THESE", "THOSE", "THEIR", "WOULD", "COULD", "SHALL",
    "SHOULD", "ABOVE", "BELOW", "UNDER", "SMALL", "LARGE", "HEAVY", "THICK", "SWEET", "SALTY",
    "BITTER", "FRESH", "CLEAN", "DIRTY", "EMPTY", "QUIET", "NOISY", "YOUNG", "SHARP", "BLUNT",
    "ROUGH", "SMOOTH", "TIGHT", "LOOSE", "BRAVE", "SMART", "FUNNY", "ANGRY", "LUCKY", "PROUD",
    "SORRY", "TIRED", "ALIVE", "HUMAN", "CHILD", "WOMAN", "PEOPLE", "FRIEND", "FAMILY", "CROWD",
    "GROUP", "CLASS", "STAFF", "POWER", "FORCE", "SPEED", "LEVEL", "POINT", "SCORE", "VALUE",
    "COUNT", "TOTAL", "SHARE", "PRICE", "COSTS", "MONEY", "DOLLAR", "RUPEE", "TRADE", "STOCK",
    "MARKET", "STORE", "BRAND", "ORDER", "OFFER", "SALES", "SPEND", "SAVED", "BANKS", "LOANS",
    "VIDEO", "AUDIO", "IMAGE", "PHOTO", "PIXEL", "CLICK", "PRESS", "TOUCH", "INPUT", "MOUSE",
    "BOARD", "DRIVE", "FILES", "SPACE", "ENTER", "SHIFT", "RESET", "LOGIN", "ADMIN", "USERS",
    "TIGER", "LION", "ZEBRA", "HORSE", "CAMEL", "SHEEP", "PANDA", "EAGLE", "SHARK", "WHALE",
    "SNAKE", "MOUSE", "RABBIT", "PUPPY", "KITTY", "BIRDS", "DUCKS", "GEESE", "PLANT", "TREES",
    "GRASS", "FLOWER", "ROSES", "TULIP", "LEAFY", "ROOTS", "SEEDS", "GROWN", "FARMS", "CROPS",
    "STORM", "RAINY", "SUNNY", "WINDY", "SNOWY", "FOGGY", "MISTY", "CLEAR", "HUMID", "FROST",
    "STONE", "STEEL", "METAL", "GLASS", "BRICK", "WOODS", "PLASTIC", "GOLD", "SILVER", "COPPER",
    "READY", "START", "HELLO"
}

# --- 🔥 TARGET WORDS ---
WORD_LIST = [
    {"word": "APPLE", "phonetic": "/ˈæp.əl/", "meaning": "A round fruit with red or green skin."},
    {"word": "TIGER", "phonetic": "/ˈtaɪ.ɡər/", "meaning": "A large wild cat with stripes."},
    {"word": "BREAD", "phonetic": "/bred/", "meaning": "Baked food made of flour and water."},
    {"word": "CHAIR", "phonetic": "/tʃeər/", "meaning": "A seat with a back and legs."},
    {"word": "SMILE", "phonetic": "/smaɪl/", "meaning": "A happy expression on the face."},
    {"word": "BEACH", "phonetic": "/biːtʃ/", "meaning": "Sandy area next to the sea."},
    {"word": "DREAM", "phonetic": "/driːm/", "meaning": "Images in mind while sleeping."},
    {"word": "LIGHT", "phonetic": "/laɪt/", "meaning": "Makes things visible."},
    {"word": "HEART", "phonetic": "/hɑːt/", "meaning": "Organ that pumps blood."},
    {"word": "WATCH", "phonetic": "/wɒtʃ/", "meaning": "Small clock worn on wrist."},
    {"word": "WATER", "phonetic": "/ˈwɔː.tər/", "meaning": "Clear liquid essential for life."},
    {"word": "MUSIC", "phonetic": "/ˈmjuː.zɪk/", "meaning": "Sounds arranged in a pleasing way."},
    {"word": "MONEY", "phonetic": "/ˈmʌn.i/", "meaning": "Coins or notes used to buy things."},
    {"word": "HOUSE", "phonetic": "/haʊs/", "meaning": "Building for people to live in."},
    {"word": "WORLD", "phonetic": "/wɜːld/", "meaning": "The earth and all people on it."},
    {"word": "PHONE", "phonetic": "/fəʊn/", "meaning": "Device used to talk to others."},
    {"word": "TABLE", "phonetic": "/ˈteɪ.bəl/", "meaning": "Furniture with a flat top and legs."},
    {"word": "PAPER", "phonetic": "/ˈpeɪ.pər/", "meaning": "Material used for writing or printing."},
    {"word": "RIVER", "phonetic": "/ˈrɪv.ər/", "meaning": "Large natural stream of water."},
    {"word": "NIGHT", "phonetic": "/naɪt/", "meaning": "Time when it is dark."},
    {"word": "HAPPY", "phonetic": "/ˈhæp.i/", "meaning": "Feeling or showing pleasure."},
    {"word": "GREEN", "phonetic": "/ɡriːn/", "meaning": "Color of grass and leaves."},
    {"word": "QUICK", "phonetic": "/kwɪk/", "meaning": "Moving fast or doing something fast."},
    {"word": "ZEBRA", "phonetic": "/ˈzeb.rə/", "meaning": "African wild horse with black and white stripes."},
    {"word": "CLOUD", "phonetic": "/klaʊd/", "meaning": "White or grey mass in the sky."},
    {"word": "SNAKE", "phonetic": "/sneɪk/", "meaning": "Long reptile with no legs."},
    {"word": "GHOST", "phonetic": "/ɡəʊst/", "meaning": "Spirit of a dead person."},
    {"word": "ROBOT", "phonetic": "/ˈrəʊ.bɒt/", "meaning": "Machine controlled by computer."},
    {"word": "PIZZA", "phonetic": "/ˈpiːt.sə/", "meaning": "Italian dish with dough, cheese, and tomato."},
    {"word": "QUEEN", "phonetic": "/kwiːn/", "meaning": "Female ruler of a country."}
]

# Ensure targets are valid
for w in WORD_LIST:
    VALID_GUESSES.add(w["word"])

# --- 🔥 AUTO END JOB ---
async def auto_end_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    
    if chat_id in active_games:
        game = active_games[chat_id]
        target_word = game['target']
        
        # Unpin
        try: await context.bot.unpin_chat_message(chat_id, game['message_id'])
        except: pass

        del active_games[chat_id]
        
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ **Time's Up!**\nGame end kar diya gaya.\n\n📝 Correct Word: **{target_word}**",
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass

# --- HELPER: GENERATE GRID ---
def generate_grid_string(target, guesses):
    target = target.upper()
    grid_msg = ""

    for guess in guesses:
        guess = guess.upper()
        row_emoji = ""
        
        for i, char in enumerate(guess):
            if char == target[i]:
                row_emoji += "🟩"
            elif char in target:
                row_emoji += "🟨"
            else:
                row_emoji += "🟥"
        
        # Formatting: 🟥🟥🟩🟥🟥   S M A I L
        formatted_word = " ".join(list(guess))
        grid_msg += f"{row_emoji}    `{formatted_word}`\n"
        
    return grid_msg

# --- COMMANDS ---

async def start_wordseek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

    chat_id = update.effective_chat.id
    
    if chat_id in active_games:
        warn = await update.message.reply_text("⚠️ Game pehle se chal raha hai!", quote=False)
        await asyncio.sleep(3)
        try: await warn.delete()
        except: pass
        return

    word_data = random.choice(WORD_LIST)
    
    msg = await update.message.reply_text("🎮 **Starting Word Challenge...**")
    
    # Pin Message
    try: await msg.pin()
    except: pass

    timer_job = None
    if context.job_queue:
        timer_job = context.job_queue.run_once(auto_end_job, 300, data=chat_id)

    active_games[chat_id] = {
        "target": word_data['word'].upper(),
        "data": word_data,
        "guesses": [],
        "message_id": msg.message_id,
        "timer_job": timer_job 
    }
    
    length = len(word_data['word'])
    hint = word_data['meaning']

    text = (
        f"🔥 **WORD GRID CHALLENGE** 🔥\n\n"
        f"🔡 Word Length: **{length} Letters**\n"
        f"👇 *Guess the word below!*\n\n"
        f"> 💡 **Hint:** {hint}"
    )
    
    # 🔥 INLINE BUTTON FOR STOP
    kb = [[InlineKeyboardButton("🛑 End Game", callback_data="end_wordseek")]]
    
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def stop_wordseek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Command se stop
    try: await update.message.delete()
    except: pass
    await end_game_logic(update.effective_chat.id, context, update)

# --- INLINE BUTTON HANDLER (New) ---
async def end_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    chat = update.effective_chat
    user = update.effective_user
    
    # Check Admin
    is_admin = False
    try:
        member = await chat.get_member(user.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            is_admin = True
    except: pass
    
    if not is_admin:
        await q.answer("❌ Only Admins can end the game!", show_alert=True)
        return

    await q.answer("🛑 Ending Game...")
    await end_game_logic(chat.id, context, update)

# --- SHARED END LOGIC ---
async def end_game_logic(chat_id, context, update):
    if chat_id in active_games:
        game = active_games[chat_id]
        
        job = game.get("timer_job")
        if job: job.schedule_removal()
        
        try: await context.bot.unpin_chat_message(chat_id, game['message_id'])
        except: pass
        
        del active_games[chat_id]
        
        # Agar callback se aaya hai to edit karo, warna new msg
        if update.callback_query:
            await update.callback_query.message.edit_text("🛑 **Game Ended by Admin!**", parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id, "🛑 **Game Ended!**", parse_mode=ParseMode.MARKDOWN)
    else:
        if not update.callback_query:
            warn = await context.bot.send_message(chat_id, "❌ Koi game nahi chal raha.")
            await asyncio.sleep(3)
            try: await warn.delete()
            except: pass

# --- GUESS HANDLER ---
async def handle_word_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in active_games: return
    
    game = active_games[chat.id]
    target = game['target']
    
    if not update.message or not update.message.text: return
    user_guess = update.message.text.strip().upper()
    
    # 1. Length Check
    if len(user_guess) != len(target): return

    # 🔥 DELETE USER MESSAGE
    try: await update.message.delete()
    except: pass

    # 2. VALIDATION
    if user_guess not in VALID_GUESSES:
        warn = await update.message.reply_text(f"⚠️ **{user_guess}** is not a valid word!", quote=False)
        await asyncio.sleep(2)
        try: await warn.delete()
        except: pass
        return

    # 3. DUPLICATE CHECK
    if user_guess in game['guesses']:
        warn = await update.message.reply_text(f"⚠️ **{user_guess}** is already guessed!", quote=False)
        await asyncio.sleep(2)
        try: await warn.delete()
        except: pass
        return

    # Reset Timer
    old_job = game.get("timer_job")
    if old_job: old_job.schedule_removal()
    new_job = None
    if context.job_queue:
        new_job = context.job_queue.run_once(auto_end_job, 300, data=chat.id)
    game['timer_job'] = new_job

    game['guesses'].append(user_guess)
    
    # WIN SCENARIO
    if user_guess == target:
        user = update.effective_user
        points = 9
        update_wordseek_score(user.id, user.first_name, points, str(chat.id))
        
        if new_job: new_job.schedule_removal()
        try: await context.bot.unpin_chat_message(chat.id, game['message_id'])
        except: pass
        
        data = game['data']
        del active_games[chat.id]
        
        await update.message.reply_text(
            f"🚬 ~ ` {user.first_name} ` ~ 🍷\n"
            f"{user_guess.title()}\n\n"
            f"Congrats! You guessed it correctly.\n"
            f"Added {points} to the leaderboard.\n"
            f"Start with /new\n\n"
            f"> **Correct Word:** {data['word']}\n"
            f"> **{data['word']}** {data.get('phonetic', '')}\n"
            f"> **Meaning:** {data['meaning']}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # WRONG GUESS - UPDATE GRID
        try:
            grid_text = generate_grid_string(target, game['guesses'])
            hint = game['data']['meaning']
            
            new_text = (
                f"🔥 **WORD GRID CHALLENGE** 🔥\n\n"
                f"{grid_text}\n"
                f"> 💡 **Hint:** {hint}"
            )
            
            # Button wapis lagana padega edit ke waqt
            kb = [[InlineKeyboardButton("🛑 End Game", callback_data="end_wordseek")]]
            
            await context.bot.edit_message_text(
                chat_id=chat.id,
                message_id=game['message_id'],
                text=new_text,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass

# --- LEADERBOARD & CALLBACKS ---
async def wordseek_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    kb = [[InlineKeyboardButton("🌍 Global Top", callback_data="wrank_global"), InlineKeyboardButton("👥 Group Top", callback_data="wrank_group")]]
    await update.message.reply_text("🏆 **WordSeek Leaderboard**\nSelect Category 👇", reply_markup=InlineKeyboardMarkup(kb))

async def wordseek_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    
    # 🔥 END BUTTON HANDLER
    if data == "end_wordseek":
        await end_game_callback(update, context)
        return

    if data.startswith("wrank_"):
        mode = data.split("_")[1]
        group_id = str(update.effective_chat.id) if mode == "group" else None
        
        leaderboard = get_wordseek_leaderboard(group_id)
        title = "🌍 Global" if mode == "global" else "👥 Group"
        msg = f"🏆 **{title} Leaderboard** 🏆\n\n"
        
        if not leaderboard: msg += "❌ No Data Found!"
        else:
            for i, p in enumerate(leaderboard, 1):
                score = p.get('global_score', 0) if mode == "global" else p.get('group_scores', {}).get(group_id, 0)
                msg += f"{i}. {p['name']} - 💎 {score}\n"
        
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="close_wrank")]]
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    if data == "close_wrank": await q.message.delete()
