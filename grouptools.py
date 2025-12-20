from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import add_warning, remove_warning, reset_warnings
from config import OWNER_ID

# --- HELPER: CHECK ADMIN ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check karega ki command chalane wala Admin hai ya nahi"""
    user = update.effective_user
    chat = update.effective_chat
    
    if user.id == OWNER_ID: return True
    
    try:
        member = await chat.get_member(user.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

# --- COMMANDS ---

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete() # Auto Delete Command
    except: pass

    if not await is_admin(update, context): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply to a user to warn!")

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    # Database call
    count = add_warning(chat.id, target.id)
    
    if count >= 3:
        # Ban logic
        await chat.ban_member(target.id)
        reset_warnings(chat.id, target.id)
        await update.message.reply_text(f"🚫 **Banned!** {target.first_name} reached 3 warnings.")
    else:
        await update.message.reply_text(f"⚠️ **Warning!** {target.first_name} ({count}/3)")

async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    count = remove_warning(chat.id, target.id)
    await update.message.reply_text(f"✅ **Unwarned!** {target.first_name} now has {count} warnings.")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    # Restrict permissions
    await chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=False))
    await update.message.reply_text(f"🔇 **Muted!** {target.first_name}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    # Restore permissions (True = allow)
    await chat.restrict_member(
        target.id, 
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True
        )
    )
    await update.message.reply_text(f"🔊 **Unmuted!** {target.first_name}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    await update.effective_chat.ban_member(target.id)
    await update.message.reply_text(f"🚫 **Banned!** {target.first_name}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    await update.effective_chat.unban_member(target.id)
    await update.message.reply_text(f"✅ **Unbanned!** {target.first_name}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    # Ban and immediately Unban = Kick
    await update.effective_chat.ban_member(target.id)
    await update.effective_chat.unban_member(target.id)
    await update.message.reply_text(f"🦵 **Kicked!** {target.first_name}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    
    # Default Level 1 (Basic)
    can_change_info = False
    can_delete = True
    can_invite = True
    can_pin = False
    
    # Check args (1, 2, or 3)
    if context.args:
        level = context.args[0]
        if level == "2":
            can_pin = True
            can_change_info = True
        elif level == "3":
            can_pin = True
            can_change_info = True
            # Full logic depends on bot rights, keeping it simple
            
    try:
        await update.effective_chat.promote_member(
            user_id=target.id,
            can_delete_messages=can_delete,
            can_invite_users=can_invite,
            can_pin_messages=can_pin,
            can_change_info=can_change_info,
            is_anonymous=False
        )
        await update.message.reply_text(f"👮‍♂️ **Promoted!** {target.first_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    target = update.message.reply_to_message.from_user
    try:
        await update.effective_chat.promote_member(
            user_id=target.id,
            can_delete_messages=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_change_info=False,
            is_anonymous=False
        )
        await update.message.reply_text(f"⬇️ **Demoted!** {target.first_name}")
    except:
        await update.message.reply_text("❌ Failed. Check my permissions.")

async def set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    if not context.args: return
    title = " ".join(context.args)
    target = update.message.reply_to_message.from_user
    
    try:
        await update.effective_chat.set_administrator_custom_title(target.id, title)
        await update.message.reply_text(f"🏷 **Title Set:** {title}")
    except:
        await update.message.reply_text("❌ Error. Needs 'Can Promote' rights.")

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    try:
        await update.message.reply_to_message.pin()
    except: pass

async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    try:
        await update.effective_chat.unpin_all_messages() # Simple unpin all or current
        # Note: Unpinning specific msg without ID is hard via command usually unpins latest
    except: pass

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete() # Delete command
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return

    try:
        await update.message.reply_to_message.delete() # Delete replied msg
    except:
        await update.message.reply_text("❌ Can't delete.")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    text = (
        "🛡️ **Admin Commands** (Works with . or /)\n\n"
        "🔸 `.warn` - Warn user (3 = Ban)\n"
        "🔸 `.unwarn` - Remove warning\n"
        "🔸 `.mute` - Mute user\n"
        "🔸 `.unmute` - Unmute user\n"
        "🔸 `.ban` - Ban user\n"
        "🔸 `.unban` - Unban user\n"
        "🔸 `.kick` - Kick user\n"
        "🔸 `.promote` - Promote (Use 1, 2, 3 for levels)\n"
        "🔸 `.demote` - Demote admin\n"
        "🔸 `.title [text]` - Set admin title\n"
        "🔸 `.pin` - Pin message\n"
        "🔸 `.d` - Delete replied message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
