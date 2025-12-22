import html
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from search import download_song
# 🔥 IMPORT REAL ENGINE
from music_engine import play_audio, stop_audio

# Fancy Text
def to_fancy(text):
    mapping = {'A': 'Λ', 'E': 'Є', 'S': 'δ', 'O': 'σ', 'T': 'ᴛ', 'N': 'ɴ', 'M': 'ᴍ', 'U': 'ᴜ', 'R': 'ʀ', 'D': 'ᴅ', 'C': 'ᴄ', 'P': 'ᴘ', 'G': 'ɢ', 'B': 'ʙ', 'L': 'ʟ', 'W': 'ᴡ', 'K': 'ᴋ', 'J': 'ᴊ', 'Y': 'ʏ', 'I': 'ɪ', 'H': 'ʜ'}
    return "".join(mapping.get(c.upper(), c) for c in text)

async def play_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("⚠️ **Usage:** `/play Song Name`")
        return

    query = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 **Searching & Downloading:** `{query}`...\n_(Thoda time lagega)_")

    # 1. DOWNLOAD SONG (Real Logic)
    # Loop me run karenge taaki bot hang na ho
    loop = asyncio.get_running_loop()
    track = await loop.run_in_executor(None, download_song, query)
    
    if not track:
        await msg.edit_text("❌ Song Download Failed! Try another name.")
        return

    await msg.edit_text("🎧 **Starting Voice Chat...**")

    # 2. PLAY AUDIO (Call PyTgCalls)
    success = await play_audio(chat_id, track['path'])

    if success:
        # 3. SHOW BANNER
        caption = f"""
<blockquote><b>🎵 {to_fancy("NOW PLAYING")}</b></blockquote>

<blockquote>
<b>📌 Title:</b> <a href='{track['url']}'>{html.escape(track['title'])}</a>
<b>⏱ Duration:</b> {track['duration']}
<b>🎤 Artist:</b> {track['channel']}
</blockquote>

<blockquote>
<b>👤 Requested by:</b> <a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>
</blockquote>
"""
        kb = [
            [InlineKeyboardButton("⏹ Stop & Leave", callback_data="music_stop")],
            [InlineKeyboardButton("❌ Close", callback_data="close_music")]
        ]

        if track['thumb']:
            await update.message.reply_photo(photo=track['thumb'], caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(text=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
        await msg.delete()
    else:
        await msg.edit_text("❌ **Error:** Assistant Group me Join nahi kar pa raha!\nMake sure Assistant is Admin or Group VC is ON.")

async def music_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    chat_id = update.effective_chat.id

    if data == "close_music":
        await q.message.delete()
    
    elif data == "music_stop":
        await stop_audio(chat_id)
        await q.answer("⏹ Music Stopped!")
        await q.message.edit_caption(caption="<blockquote><b>🛑 Music Stopped.</b></blockquote>", parse_mode=ParseMode.HTML)
