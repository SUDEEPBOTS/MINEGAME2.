from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import add_warning, remove_warning, reset_warnings
from config import OWNER_ID


# ─────────────────────────────
# HELPERS
# ─────────────────────────────
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if str(user.id) == str(OWNER_ID):
        return True

    if chat.type == "private":
        await update.message.reply_text("❌ Ye command sirf group me kaam karti hai.")
        return False

    try:
        member = await chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return True
    except:
        pass

    await update.message.reply_text(
        "❌ **Access Denied!** Sirf Admins ye command use kar sakte hain.",
        parse_mode=ParseMode.MARKDOWN
    )
    return False


async def require_reply(update: Update, text: str):
    if not update.message.reply_to_message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return False
    return True


async def safe_delete(msg):
    try:
        await msg.delete()
    except:
        pass


# ─────────────────────────────
# WARN SYSTEM
# ─────────────────────────────
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.warn` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat

    if str(target.id) == str(OWNER_ID) or target.is_bot:
        return await chat.send_message("❌ Owner ya bot ko warn nahi kar sakte!")

    count = add_warning(chat.id, target.id)

    if count >= 3:
        await chat.ban_member(target.id)
        reset_warnings(chat.id, target.id)
        await chat.send_message(f"🚫 **BANNED!**\n👤 {target.first_name} (3 warnings)")
    else:
        await chat.send_message(f"⚠️ **WARNING!**\n👤 {target.first_name}\nCount: {count}/3")


async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.unwarn` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    count = remove_warning(update.effective_chat.id, target.id)

    await update.effective_chat.send_message(
        f"✅ **Unwarned!**\n👤 {target.first_name}\nRemaining: {count}"
    )


# ─────────────────────────────
# MUTE / UNMUTE
# ─────────────────────────────
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.mute` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    await update.effective_chat.restrict_member(
        target.id, ChatPermissions(can_send_messages=False)
    )
    await update.effective_chat.send_message(f"🔇 **Muted!** {target.first_name}")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.unmute` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    await update.effective_chat.restrict_member(
        target.id,
        ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_send_polls=True
        )
    )
    await update.effective_chat.send_message(f"🔊 **Unmuted!** {target.first_name}")


# ─────────────────────────────
# BAN / UNBAN / KICK
# ─────────────────────────────
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.ban` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    await update.effective_chat.ban_member(target.id)
    await update.effective_chat.send_message(f"🚫 **BANNED!** {target.first_name}")


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.unban` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    await update.effective_chat.unban_member(target.id)
    await update.effective_chat.send_message(f"✅ **Unbanned!** {target.first_name}")


async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.kick` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    chat = update.effective_chat
    await chat.ban_member(target.id)
    await chat.unban_member(target.id)
    await chat.send_message(f"🦵 **Kicked!** {target.first_name}")


# ─────────────────────────────
# PROMOTE / DEMOTE / TITLE
# ─────────────────────────────
async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.promote 1/2/3` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    level = context.args[0] if context.args else "1"

    perms = dict(
        can_delete_messages=True,
        can_invite_users=True,
        can_pin_messages=False,
        can_change_info=False,
        is_anonymous=False
    )

    if level in ("2", "3"):
        perms["can_pin_messages"] = True
        perms["can_change_info"] = True

    await update.effective_chat.promote_member(target.id, **perms)
    await update.effective_chat.send_message(
        f"👮‍♂️ **Promoted!** {target.first_name} (Level {level})"
    )


async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.demote` use karo."):
        return

    await safe_delete(update.message)

    target = update.message.reply_to_message.from_user
    await update.effective_chat.promote_member(
        target.id,
        can_delete_messages=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_change_info=False,
        is_anonymous=False
    )
    await update.effective_chat.send_message(f"⬇️ **Demoted!** {target.first_name}")


async def set_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.title <text>` use karo."):
        return
    if not context.args:
        return

    await safe_delete(update.message)

    title = " ".join(context.args)
    target = update.message.reply_to_message.from_user
    await update.effective_chat.set_administrator_custom_title(target.id, title)
    await update.effective_chat.send_message(f"🏷 **Title Set:** {title}")


# ─────────────────────────────
# PIN / UNPIN / DELETE
# ─────────────────────────────
async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.pin` use karo."):
        return

    await safe_delete(update.message)
    await update.message.reply_to_message.pin()


async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    await safe_delete(update.message)
    await update.effective_chat.unpin_all_messages()
    await update.effective_chat.send_message("✅ All messages unpinned.")


async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not await require_reply(update, "⚠️ Reply karke `.d` use karo."):
        return

    await safe_delete(update.message)
    await update.message.reply_to_message.delete()


# ─────────────────────────────
# ADMIN HELP
# ─────────────────────────────
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_delete(update.message)

    text = (
        "🛡️ **Admin Commands (.prefix only)**\n\n"
        ".warn [reply] - Warn a user (3 = ban)\n"
        ".unwarn [reply] - Remove 1 warning\n"
        ".mute [reply] - Mute user\n"
        ".unmute [reply] - Unmute user\n"
        ".ban [reply] - Ban user\n"
        ".unban [reply] - Unban user\n"
        ".kick [reply] - Kick from group\n"
        ".promote [reply] 1/2/3 - Promote admin\n"
        ".demote [reply] - Demote admin\n"
        ".title [reply] <text> - Set admin title\n"
        ".pin [reply] - Pin message\n"
        ".unpin - Unpin all messages\n"
        ".d [reply] - Delete message\n"
        ".help - Show this help"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)