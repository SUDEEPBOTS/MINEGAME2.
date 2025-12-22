import random
import string
import io
import html
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# --- WORD DATABASE ---
WORDS_POOL = [
    "LOVE", "FOREVER", "DIGAN", "PYTHON", "GAME", "FRIEND", 
    "COUPLE", "HEART", "MUSIC", "VIBE", "TRIBE", "INDIA",
    "BOT", "CODE", "HAPPY", "SMILE", "TRUST", "PEACE",
    "DREAM", "NIGHT", "PARTY", "MONEY", "POWER", "KING"
]

# --- GAME STORAGE ---
active_games = {}

# --- SETTINGS ---
GRID_SIZE = 8
CELL_SIZE = 60
FONT_PATH = "arial.ttf"

# Fancy Text Converter
def to_fancy(text):
    mapping = {'A': 'Λ', 'E': 'Є', 'S': 'δ', 'O': 'σ', 'T': 'ᴛ', 'N': 'ɴ', 'M': 'ᴍ', 'U': 'ᴜ', 'R': 'ʀ', 'D': 'ᴅ', 'C': 'ᴄ', 'P': 'ᴘ', 'G': 'ɢ', 'B': 'ʙ', 'L': 'ʟ', 'W': 'ᴡ', 'K': 'ᴋ', 'J': 'ᴊ', 'Y': 'ʏ', 'I': 'ɪ', 'H': 'ʜ'}
    return "".join(mapping.get(c.upper(), c) for c in text)

# --- HELPER: CREATE HINT ---
def create_hint(word):
    chars = list(word)
    num_to_hide = len(word) // 2 
    indices_to_hide = random.sample(range(len(word)), num_to_hide)
    for i in indices_to_hide:
        chars[i] = "＿"
    return " ".join(chars)

# --- 1. GENERATE GRID ---
def generate_grid():
    targets = random.sample(WORDS_POOL, 5)
    grid = [['' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for word in targets:
        placed = False
        attempts = 0
        while not placed and attempts < 100:
            direction = random.choice(['H', 'V']) 
            if direction == 'H':
                row = random.randint(0, GRID_SIZE - 1)
                col = random.randint(0, GRID_SIZE - len(word))
                if all(grid[row][col+i] == '' or grid[row][col+i] == word[i] for i in range(len(word))):
                    for i in range(len(word)): grid[row][col+i] = word[i]
                    placed = True
            else: 
                row = random.randint(0, GRID_SIZE - len(word))
                col = random.randint(0, GRID_SIZE - 1)
                if all(grid[row+i][col] == '' or grid[row+i][col] == word[i] for i in range(len(word))):
                    for i in range(len(word)): grid[row+i][col] = word[i]
                    placed = True
            attempts += 1
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == '': grid[r][c] = random.choice(string.ascii_uppercase)
    return grid, targets

# --- 2. DRAW IMAGE ---
def draw_grid_image(grid):
    width = GRID_SIZE * CELL_SIZE
    height = GRID_SIZE * CELL_SIZE + 60 
    img = Image.new('RGB', (width, height), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, 30); header_font = ImageFont.truetype(FONT_PATH, 40)
    except:
        font = ImageFont.load_default(); header_font = ImageFont.load_default()
    draw.rectangle([0, 0, width, 60], fill="#0088cc") 
    text = "WORD GRID"
    bbox = draw.textbbox((0, 0), text, font=header_font)
    w = bbox[2] - bbox[0]
    draw.text(((width - w)/2, 10), text, fill="white", font=header_font)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            x = c * CELL_SIZE; y = r * CELL_SIZE + 60
            draw.rectangle([x, y, x+CELL_SIZE, y+CELL_SIZE], outline="#dddddd", width=1)
            letter = grid[r][c]
            bbox = draw.textbbox((0, 0), letter, font=font)
            lw = bbox[2] - bbox[0]; lh = bbox[3] - bbox[1]
            draw.text((x + (CELL_SIZE-lw)/2, y + (CELL_SIZE-lh)/2), letter, fill="black", font=font)
    bio = io.BytesIO(); img.save(bio, format="JPEG"); bio.seek(0)
    return bio

# --- 3. START COMMAND ---
async def start_wordgrid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    grid, targets = generate_grid()
    photo = draw_grid_image(grid)
    hints = {word: create_hint(word) for word in targets}
    active_games[chat_id] = {'grid': grid, 'targets': targets, 'hints': hints, 'found': []}
    
    word_list_text = "\n".join([f"▫️ <code>{hints[w]}</code>" for w in targets])
    
    caption = f"""
<blockquote><b>🧩 {to_fancy("WORD GRID CHALLENGE")}</b></blockquote>

<blockquote>
{word_list_text}
</blockquote>

<blockquote>
<b>👇 Type the FULL word to solve!</b>
<b>👨‍💻 Dev:</b> Digan
</blockquote>
"""
    kb = [[InlineKeyboardButton("🏳️ Give Up", callback_data="giveup_wordgrid")]]
    msg = await update.message.reply_photo(
        photo=photo,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML
    )
    active_games[chat_id]['msg_id'] = msg.message_id

# --- 4. HANDLE GUESS ---
async def handle_word_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    chat_id = update.effective_chat.id
    text = update.message.text.upper().strip()
    if chat_id not in active_games: return
    game = active_games[chat_id]
    
    if text in game['targets'] and text not in game['found']:
        game['found'].append(text)
        if len(game['found']) == len(game['targets']):
            del active_games[chat_id]
            await update.message.reply_text(f"<blockquote><b>🏆 {to_fancy("WINNER")}!</b>\n\nYou solved the grid! ✅</blockquote>", parse_mode=ParseMode.HTML)
            return

        new_list = []
        for w in game['targets']:
            if w in game['found']: new_list.append(f"✅ <s>{w}</s>")
            else: new_list.append(f"▫️ <code>{game['hints'][w]}</code>")
        
        caption = f"""
<blockquote><b>🧩 {to_fancy("WORD GRID CHALLENGE")}</b></blockquote>

<blockquote>
{"\n".join(new_list)}
</blockquote>

<blockquote>
<b>👇 Type the FULL word to solve!</b>
<b>👨‍💻 Dev:</b> Digan
</blockquote>
"""     
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=game['msg_id'],
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏳️ Give Up", callback_data="giveup_wordgrid")]])
            )
            await update.message.set_reaction("👍")
        except: pass

async def give_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_games:
        targets = active_games[chat_id]['targets']
        del active_games[chat_id]
        await update.callback_query.message.edit_caption(
            caption=f"<blockquote><b>❌ {to_fancy("GAME OVER")}</b>\n\nWords were: {', '.join(targets)}</blockquote>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.callback_query.answer("No active game.", show_alert=True)
