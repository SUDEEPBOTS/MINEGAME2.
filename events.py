from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
# 🔥 Sabhi jaruri functions import karein
from database import register_user, check_registered, get_logger_group, update_group_activity, remove_group

# --- 1. WELCOME USER & BOT ADD LOG ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    chat = update.effective_chat
    user = update.effective_user # Jisne add kiya ya jo join hua
    
    # 🟢 STEP 1: Group Activity Update (Stats ke liye)
    try:
        update_group_activity(chat.id, chat.title)
    except Exception as e:
        print(f"DB Error (update_group_activity): {e}")

    for member in update.message.new_chat_members:
        # 🤖 A. AGAR BOT ADD HUA (Logger Log)
        if member.id == context.bot.id:
            await update.message.reply_text(
                "😎 **Thanks for adding me!**\nMake me **Admin** to use full power! ⚡",
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger_id = get_logger_group()
            if logger_id:
                txt = (
                    "🟢 **BOT ADDED TO NEW GROUP**\n\n"
                    f"📍 **Group:** {chat.title}\n"
                    f"🆔 **Group ID:** `{chat.id}`\n"
                    f"👤 **Added By:** {user.first_name if user else 'Unknown'} (@{user.username if user and user.username else 'NoUser'})\n"
                    f"🆔 **User ID:** `{user.id if user else 'N/A'}`"
                )
                kb = [[InlineKeyboardButton("❌ Close", callback_data="close_log")]]
                try:
                    await context.bot.send_message(
                        chat_id=logger_id, 
                        text=txt, 
                        reply_markup=InlineKeyboardMarkup(kb), 
                        parse_mode=ParseMode.MARKDOWN
                    )
                except: 
                    pass
            continue
            
        # 👤 B. NORMAL USER JOIN HUA
        if not member.is_bot:
            if not check_registered(member.id):
                register_user(member.id, member.first_name)
            
            # Welcome Message (Optional: Isko group settings ke mutabik on/off kar sakte hain)
            try:
                await update.message.reply_text(
                    f"👋 **Welcome {member.first_name}!**\nWelcome to **{chat.title}** ❤️",
                    parse_mode=ParseMode.MARKDOWN
                )
            except: 
                pass

# --- 2. TRACK LEAVE (BOT REMOVE & STATS FIX) ---
async def track_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.left_chat_member:
        return

    left_user = update.message.left_chat_member
    action_by = update.message.from_user # Jisne nikala ya jisne leave kiya
    chat = update.effective_chat
    
    # 🤖 A. AGAR BOT NIKALA GAYA / LEFT HUA
    if left_user.id == context.bot.id:
        
        # 🔥 STEP 1: Database se Group Hatao (Taki Stats/Count sahi ho jaye)
        try:
            remove_group(chat.id)
        except Exception as e:
            print(f"DB Error (remove_group): {e}")
        
        # 🔥 STEP 2: Logger me Update Bhejo
        logger_id = get_logger_group()
        if logger_id:
            txt = (
                "🔴 **BOT REMOVED / LEFT GC**\n\n"
                f"📍 **Group Name:** {chat.title}\n"
                f"🆔 **Group ID:** `{chat.id}`\n"
                f"👮 **Action By:** {action_by.first_name if action_by else 'System'}\n"
                f"🆔 **Admin ID:** `{action_by.id if action_by else 'N/A'}`"
            )
            kb = [[InlineKeyboardButton("❌ Close", callback_data="close_log")]]
            try:
                await context.bot.send_message(
                    chat_id=logger_id, 
                    text=txt, 
                    reply_markup=InlineKeyboardMarkup(kb), 
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        return 

    # 👤 B. NORMAL USER LEFT (Quietly ignore, no DB delete needed for users usually)
