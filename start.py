import time
import psutil
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import check_registered, register_user
from config import OWNER_ID, OWNER_NAME
# 🔥 Import Random Sticker Logic
from ai_chat import get_mimi_sticker

# --- GLOBAL VARS ---
START_IMG = "https://i.ibb.co/WLB2B31/1000007092.png" 
BOT_START_TIME = time.time()
SUPPORT_LINK = "https://t.me/+N08m5L1mCTU2NTE1"

# --- HELPER: GET UPTIME ---
def get_readable_time():
    seconds = int(time.time() - BOT_START_TIME)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d > 0:
        return f"{d}d:{h}h:{m}m:{s}s"
    return f"{h}h:{m}m:{s}s"

# --- MAIN START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_name = context.bot.first_name
    bot_username = context.bot.username
    
    # --- 1. ANIMATION SEQUENCE ---
    
    # A. Send Random Sticker (From Admin Packs)
    try:
        sticker_id = await get_mimi_sticker(context.bot)
        if sticker_id:
            stk = await update.message.reply_sticker(sticker=sticker_id)
            await asyncio.sleep(2) # 2 Second wait
            await stk.delete()     # Delete Sticker
    except: pass 

    # B. Send Emoji & Loading Bar
    msg = await update.message.reply_text("⚡")
    await asyncio.sleep(0.5)
    
    # Loading Animation Loop
    bars = [
        "⚡ ʟᴏᴀᴅɪɴɢ ▒▒▒▒▒",
        "⚡ ʟᴏᴀᴅɪɴɢ █▒▒▒▒",
        "⚡ ʟᴏᴀᴅɪɴɢ ██▒▒▒",
        "⚡ ʟᴏᴀᴅɪɴɢ ███▒▒",
        "⚡ ʟᴏᴀᴅɪɴɢ ████▒",
        "⚡ ʟᴏᴀᴅɪɴɢ █████",
        "✨ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!"
    ]
    
    for bar in bars:
        try:
            await msg.edit_text(bar)
            await asyncio.sleep(0.3)
        except: pass
    
    await asyncio.sleep(0.5)
    await msg.delete() # Loading message delete

    # --- 2. SYSTEM STATS & CAPTION ---
    try:
        uptime = get_readable_time()
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
    except:
        uptime = "00:00:00"; cpu=0; ram=0; disk=0

    # Owner Link
    owner_link = f"[{OWNER_NAME}](tg://user?id={OWNER_ID})"

    caption = f"""┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼─── ⏤‌‌●
┆◍ ʜєʏ, {user.first_name} 🥀
┆◍ ɪ ᴧϻ {bot_name}
└────────────────────•
ɪ ᴀᴍ ᴛʜᴇ ғᴀsᴛᴇsᴛ ᴀɴᴅ ᴘᴏᴡᴇʀғᴜʟ ᴇᴄᴏɴᴏᴍʏ & ᴀɪ ʙᴏᴛ ᴡɪᴛʜ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ғᴇᴀᴛᴜʀᴇs.

```text
⚙️ SYSTEM STATUS
➥ UPTIME: 0h:2m:10s
➥ STORAGE: 80.4%
➥ CPU LOAD: 61.7%
➥ RAM USED: 56.1%
```

•──────────────────────•
✦ ᴘᴏᴡєʀєᴅ ʙʏ » {owner_link}
"""

    # --- 3. AUTO REGISTRATION ---
    is_new_user = False
    if not check_registered(user.id):
        register_user(user.id, user.first_name)
        is_new_user = True

    # --- 4. BUTTONS ---
    keyboard = [
        [
            InlineKeyboardButton("💬 Chat AI", callback_data="start_chat_ai"),
            InlineKeyboardButton("📊 Ranking", callback_data="help_market") 
        ],
        [
            InlineKeyboardButton("🎮 Games & Casino", callback_data="help_games"),
            InlineKeyboardButton("🛒 VIP Shop", callback_data="help_shop")
        ],
        [
            InlineKeyboardButton("🚑 Support", url=SUPPORT_LINK),
            InlineKeyboardButton("📚 Commands", callback_data="help_main")
        ],
        [
            InlineKeyboardButton("➕ Add Me To Your Group ➕", url=f"https://t.me/{bot_username}?startgroup=true")
        ]
    ]

    # --- 5. SEND MAIN MESSAGE ---
    await update.message.reply_photo(
        photo=START_IMG,
        caption=caption,
        has_spoiler=True,              # 👈 yahi 
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

    # --- 6. BONUS MESSAGE ---
    if is_new_user:
        await update.message.reply_text(
            f"🎉 **Welcome {user.first_name}!**\n"
            f"✅ Account Created Successfully.\n"
            f"💰 **You received ₹500 Free Bonus!**",
            parse_mode=ParseMode.MARKDOWN
        )

# --- CALLBACK HANDLER ---
async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user = update.effective_user
    
    # 1. HELP MAIN MENU
    if data == "help_main":
        caption = (
            f"📚 **MAIN MENU**\n"
            f"Select a category to see commands:\n\n"
            f"🏦 **Bank:** Deposit, Withdraw, Loans\n"
            f"📈 **Market:** Invest, Sell, Ranking\n"
            f"🎮 **Games:** Mines, Betting\n"
            f"🛒 **Shop:** Buy VIP, Items\n"
            f"👮 **Admin:** Group Management"
        )
        kb = [
            [InlineKeyboardButton("🏦 Bank", callback_data="help_bank"), InlineKeyboardButton("📊 Market", callback_data="help_market")],
            [InlineKeyboardButton("🎮 Games", callback_data="help_games"), InlineKeyboardButton("🛒 Shop", callback_data="help_shop")],
            # 🔥 ADMIN BUTTON ADDED HERE
            [InlineKeyboardButton("👮 Admin", callback_data="help_admin"), InlineKeyboardButton("🔮 Extra", callback_data="help_next")],
            [InlineKeyboardButton("🔙 Back Home", callback_data="back_home")]
        ]
        await q.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    # 2. SUB MENUS
    elif data == "help_bank":
        text = (
            "🏦 **BANKING SYSTEM**\n\n"
            "• `/balance` - Check wallet\n"
            "• `/bank` - Check bank account\n"
            "• `/deposit [amount]` - Save money\n"
            "• `/withdraw [amount]` - Get cash\n"
            "• `/loan` - Take loan\n"
            "• `/payloan` - Repay loan"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        await q.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    elif data == "help_market":
        text = (
            "📊 **RANKING & MARKET**\n\n"
            "• `/crank` - **Chat Leaderboard**\n"
            "• `/top` - Global Rich List\n"
            "• `/market` - View Share Prices\n"
            "• `/invest [group_id] [amount]` - Buy Shares\n"
            "• `/sell [group_id]` - Sell Shares"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        await q.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    elif data == "help_games":
        text = (
            "🎮 **GAMES & CASINO**\n\n"
            "• `/new` - WordSeek Game (New!)\n"
            "• `/bet [amount]` - Play Mines 💣\n"
            "• `/rob` - Rob someone (Reply)\n"
            "• `/kill` - Kill someone (Reply)\n"
            "• `/pay [amount]` - Give money"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        await q.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    
    elif data == "help_shop":
        text = (
            "🛒 **VIP SHOP**\n\n"
            "• `/shop` - Open Shop Menu\n"
            "• `/redeem [code]` - Get Free Money\n"
            "• `/protect` - Buy Shield (24h)"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        await q.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    # 🔥 ADMIN COMMANDS MENU 🔥
    elif data == "help_admin":
        text = (
            "👮 **ADMIN COMMANDS**\n"
            "_(Admin Rights Required)_\n\n"
            "• `.warn` / `.unwarn` - Manage Warnings\n"
            "• `.mute` / `.unmute` - Silence Users\n"
            "• `.ban` / `.unban` - Ban Users\n"
            "• `.kick` - Kick User\n"
            "• `.pin` / `.unpin` - Pin Messages\n"
            "• `.title [text]` - Set Admin Title\n"
            "• `.promote` / `.demote` - Manage Admins\n"
            "• `.d` - Delete Replied Message"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        await q.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    elif data == "help_next":
        text = (
            "🔮 **EXTRA COMMANDS**\n\n"
            "• `/alive` - Check Health\n"
            "• `/eco` - Economy Status\n"
            "• `Hi Yuki` - Chat with AI"
        )
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="help_main")]]
        await q.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

    # 3. START CHAT (AI)
    elif data == "start_chat_ai":
        await q.answer("💬 AI Mode Active!", show_alert=False)
        await q.message.reply_text(f"Hey **{user.first_name}**! 👋\nBas **'Hi Yuki'** ya **'Hello'** likho, main turant reply karungi!")

    # 4. BACK HOME
    elif data == "back_home":
        owner_link = f"[{OWNER_NAME}](tg://user?id={OWNER_ID})"
        try:
            uptime = get_readable_time()
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        except:
            uptime = "00:00:00"; cpu=0; ram=0; disk=0

        caption = f"""┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼─── ⏤‌‌●
┆◍ ʜєʏ, {user.first_name} 🥀
┆◍ ɪ ᴧϻ {context.bot.first_name}
└────────────────────•
ɪ ᴀᴍ ᴛʜᴇ ғᴀsᴛᴇsᴛ ᴀɴᴅ ᴘᴏᴡᴇʀғᴜʟ ᴇᴄᴏɴᴏᴍʏ & ᴀɪ ʙᴏᴛ ᴡɪᴛʜ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ғᴇᴀᴛᴜʀᴇs.

➥ᴜᴘᴛɪᴍᴇ: `{uptime}`
➥sᴇʀᴠᴇʀ sᴛᴏʀᴀɢᴇ: `{disk}%`
➥ᴄᴘᴜ ʟᴏᴀᴅ: `{cpu}%`
➥ʀᴀᴍ ᴄᴏɴsᴜᴍᴘᴛɪᴏɴ: `{ram}%`
•──────────────────────•
✦ᴘᴏᴡєʀєᴅ ʙʏ » {owner_link}"""

        keyboard = [
            [InlineKeyboardButton("💬 Chat AI", callback_data="start_chat_ai"), InlineKeyboardButton("📊 Ranking", callback_data="help_market")],
            [InlineKeyboardButton("🎮 Games & Casino", callback_data="help_games"), InlineKeyboardButton("🛒 VIP Shop", callback_data="help_shop")],
            [InlineKeyboardButton("🚑 Support", url=SUPPORT_LINK), InlineKeyboardButton("📚 Commands", callback_data="help_main")],
            [InlineKeyboardButton("➕ Add Me To Your Group ➕", url=f"https://t.me/{context.bot.username}?startgroup=true")]
        ]
        await q.edit_message_caption(caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
