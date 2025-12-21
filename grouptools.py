from telegram import Update, ChatPermissions
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import ContextTypes
from database import add_warning, remove_warning, reset_warnings
from config import OWNER_ID

# --- HELPER: CHECK USER ADMIN ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check karega ki command chalane wala Admin hai ya nahi"""
    user = update.effective_user
    chat = update.effective_chat
    
    # 1. Owner Check (Sabse pehle)
    try:
        if str(user.id) == str(OWNER_ID): 
            return True
    except: pass

    # 2. Private Chat Check
    if chat.type == "private":
        await update.message.reply_text("❌ Ye command sirf Group me kaam karegi.")
        return False

    # 3. Group Admin Check
    try:
        member = await chat.get_member(user.id)
        if member.status in ['administrator', 'creator']:
            return True
    except Exception as e:
        print(f"DEBUG: Admin check error: {e}")
    
    # Agar Admin nahi hai to user ko batao
    await update.message.reply_text("❌ **Access Denied!** Sirf Admins ye command use kar sakte hain.")
    return False

# --- COMMANDS ---

# 🔥 NEW: GET ID COMMAND 🔥
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Auto Delete command message (Optional)
    try: await update.message.delete()
    except: pass

    chat = update.effective_chat
    msg = update.message
    reply = msg.reply_to_message
    
    text = ""
    
    # Scenario 1: Reply to a message
    if reply:
        # Original Sender ID
        user_id = reply.from_user.id
        text += f"👤 **User ID:** `{user_id}`\n"
        
        # Check if Forwarded from User
        if reply.forward_from:
            text += f"⏩ **Forwarded User ID:** `{reply.forward_from.id}`\n"
        
        # Check if Forwarded from Channel/Group
        if reply.forward_from_chat:
            text += f"📢 **Forwarded Chat ID:** `{reply.forward_from_chat.id}`\n"
            
        # Hidden Sender (User ne privacy lagayi ho)
        if reply.forward_sender_name and not reply.forward_from and not reply.forward_from_chat:
             text += f"⏩ **Forwarded Sender:** {reply.forward_sender_name} (ID Hidden)\n"

    # Scenario 2: Direct Command (No Reply)
    else:
        user_id = update.effective_user.id
        text += f"👤 **Your User ID:** `{user_id}`\n"

    # Group ID (Always Show)
    text += f"👥 **Group ID:** `{chat.id}`"
    
    await context.bot.send_message(chat.id, text, parse_mode=ParseMode.MARKDOWN)

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass

    if not await is_admin(update, context): return

    if not update.message.reply_to_message:
    return await update.message.reply_text(
        "⚠️ **Galti!**\nKisi user ke message par reply karke ye command use karo.",
        parse_mode=ParseMode.MARKDOWN
    )

# Ab delete karo (optional)
try:
    await update.message.delete()
except:
    pass

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    if str(target.id) == str(OWNER_ID) or target.is_bot:
        return await update.message.reply_text("❌ Owner ya Bot ko warn nahi kar sakte!")

    count = add_warning(chat.id, target.id)
    
    if count >= 3:
        try:
            await chat.ban_member(target.id)
            reset_warnings(chat.id, target.id)
            await chat.send_message(f"🚫 **BANNED!**\n👤 {target.first_name} ki 3 warnings puri ho gayi.")
        except Exception as e:
            await chat.send_message(f"❌ **Error:** Main ban nahi kar pa raha.\nKya main Group Admin hoon?\nError: `{e}`")
    else:
        await chat.send_message(f"⚠️ **WARNING!**\n👤 {target.first_name}\nCount: {count}/3")

async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    count = remove_warning(chat.id, target.id)
    await chat.send_message(f"✅ **Unwarned!**\n👤 {target.first_name}\nWarnings Left: {count}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    try:
        await chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=False))
        await chat.send_message(f"🔇 **Muted!** {target.first_name} ab message nahi bhej payega.")
    except Exception as e:
        await chat.send_message(f"❌ Error: {e}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    
    try:
        await chat.restrict_member(
            target.id, 
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True
            )
        )
        await chat.send_message(f"🔊 **Unmuted!** {target.first_name} ab bol sakta hai.")
    except Exception as e:
        await chat.send_message(f"❌ Error: {e}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "⚠️ **Reply required!**\nKisi user ke message par reply karke `.ban` use karo.",
            parse_mode=ParseMode.MARKDOWN
        )

    try:
        await update.message.delete()
    except:
        pass

    target = update.message.reply_to_message.from_user
    try:
        await update.effective_chat.ban_member(target.id)
        await update.effective_chat.send_message(
            f"🚫 **BANNED!**\n👤 {target.first_name}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    target = update.message.reply_to_message.from_user
    try:
        await update.effective_chat.unban_member(target.id)
        await update.effective_chat.send_message(f"✅ **Unbanned!** {target.first_name} wapis aa sakta hai.")
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    target = update.message.reply_to_message.from_user
    try:
        await update.effective_chat.ban_member(target.id)
        await update.effective_chat.unban_member(target.id)
        await update.effective_chat.send_message(f"🦵 **Kicked!** {target.first_name}")
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    target = update.message.reply_to_message.from_user
    
    can_change_info = False
    can_delete = True
    can_invite = True
    can_pin = False
    
    if context.args:
        level = context.args[0]
        if level == "2":
            can_pin = True
            can_change_info = True
        elif level == "3":
            can_pin = True
            can_change_info = True
            
    try:
        await update.effective_chat.promote_member(
            user_id=target.id,
            can_delete_messages=can_delete,
            can_invite_users=can_invite,
            can_pin_messages=can_pin,
            can_change_info=can_change_info,
            is_anonymous=False
        )
        await update.effective_chat.send_message(f"👮‍♂️ **Promoted!** {target.first_name} is now Admin.")
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

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
        await update.effective_chat.send_message(f"⬇️ **Demoted!** {target.first_name}.")
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    if not context.args: return
    title = " ".join(context.args)
    target = update.message.reply_to_message.from_user
    
    try:
        await update.effective_chat.set_administrator_custom_title(target.id, title)
        await update.effective_chat.send_message(f"🏷 **Title Set:** {title}")
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}\n(Bot needs 'Add New Admins' permission to set titles)")

async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke use karo.")

    try:
        await update.message.reply_to_message.pin()
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return
    try:
        await update.effective_chat.unpin_all_messages() 
        await update.effective_chat.send_message("✅ All messages unpinned.")
    except Exception as e:
        await update.effective_chat.send_message(f"❌ Error: {e}")

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    if not await is_admin(update, context): return

    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: Delete nahi kar pa raha. ({e})")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    
    text = (
        "🛡️ **Admin Commands** (Works with . or /)\n\n"
        "🔸 `.id` - Get User/Group/Forward ID\n"
        "🔸 `.warn` - Warn user (3 = Ban)\n"
        "🔸 `.unwarn` - Remove warning\n"
        "🔸 `.mute` - Mute user\n"
        "🔸 `.unmute` - Unmute user\n"
        "🔸 `.ban` - Ban user\n"
        "🔸 `.unban` - Unban user\n"
        "🔸 `.kick` - Kick user\n"
        "🔸 `.promote` - Promote\n"
        "🔸 `.demote` - Demote\n"
        "🔸 `.title` - Set title\n"
        "🔸 `.pin` - Pin message\n"
        "🔸 `.d` - Delete message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
