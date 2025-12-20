from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from config import OWNER_ID
from database import (
    users_col, groups_col, codes_col, update_balance, 
    add_api_key, remove_api_key, get_all_keys,
    add_game_key, remove_game_key, get_game_keys,
    add_sticker_pack, remove_sticker_pack, get_sticker_packs,
    wipe_database, set_economy_status, get_economy_status,
    set_logger_group, delete_logger_group,
    add_voice_key, remove_voice_key, get_all_voice_keys, # 🔥 Voice Key Imports
    set_custom_voice, get_custom_voice # 🔥 TTS Imports
)

# Admin input track karne ke liye state
ADMIN_INPUT_STATE = {}

# --- 1. MAIN ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(OWNER_ID): return

    # Purani state clear karo
    if update.effective_user.id in ADMIN_INPUT_STATE:
        del ADMIN_INPUT_STATE[update.effective_user.id]
    
    eco_status = "🟢 ON" if get_economy_status() else "🔴 OFF"
    voice_id = get_custom_voice()
    voice_keys = len(get_all_voice_keys())
    chat_keys = len(get_all_keys())

    text = (
        f"👮‍♂️ **ADMIN CONTROL PANEL**\n\n"
        f"⚙️ **Economy:** {eco_status}\n"
        f"🗣 **Current Voice ID:** `{voice_id}`\n"
        f"🔑 **Voice Keys:** `{voice_keys}`\n"
        f"💬 **Chat Keys:** `{chat_keys}`\n\n"
        f"👇 Select an action to manage Mimi:"
    )

    kb = [
        [InlineKeyboardButton(f"Economy: {eco_status}", callback_data="admin_toggle_eco")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_cast_ask"), InlineKeyboardButton("🎁 Promo Code", callback_data="admin_code_ask")],
        [InlineKeyboardButton("💰 Add Money", callback_data="admin_add_ask"), InlineKeyboardButton("💸 Take Money", callback_data="admin_take_ask")],
        
        # Keys Management
        [InlineKeyboardButton("🔑 Chat Keys", callback_data="admin_chat_keys_menu"), InlineKeyboardButton("🎮 Game Keys", callback_data="admin_game_keys_menu")],
        
        # 🔥 VOICE & TTS SECTION 🔥
        [InlineKeyboardButton("🎙 Voice Keys", callback_data="admin_voice_keys_menu"), InlineKeyboardButton("🗣 Set Custom TTS", callback_data="admin_tts_set")],
        
        # Stickers & Logger
        [InlineKeyboardButton("👻 Stickers", callback_data="admin_stickers_menu"), InlineKeyboardButton("📝 Logger", callback_data="admin_logger_menu")],
        
        [InlineKeyboardButton("☢️ WIPE DATA", callback_data="admin_wipe_ask"), InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# --- 2. CALLBACK HANDLER ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    user_id = q.from_user.id
    
    if str(user_id) != str(OWNER_ID):
        await q.answer("❌ Owner Only!", show_alert=True)
        return

    # --- VOICE KEY MENU ---
    if data == "admin_voice_keys_menu":
        kb = [
            [InlineKeyboardButton("➕ Add Voice Key", callback_data="admin_vkey_add")],
            [InlineKeyboardButton("➖ Del Voice Key", callback_data="admin_vkey_del")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]
        await q.edit_message_text("🎙 **ElevenLabs Voice Keys**\nMimi ki awaaz ke liye API keys manage karein.", reply_markup=InlineKeyboardMarkup(kb))
        return

    # --- CUSTOM TTS SET ---
    if data == "admin_tts_set":
        ADMIN_INPUT_STATE[user_id] = 'set_tts_id'
        kb = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_back")]]
        await q.edit_message_text(f"🎙 **Set Custom Voice ID**\n\nElevenLabs se Voice ID bhejo.\n\n👉 Current: `{get_custom_voice()}`", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    # --- INPUT TRIGGERS ---
    if data == "admin_vkey_add":
        ADMIN_INPUT_STATE[user_id] = 'add_voice_key'
        await q.edit_message_text("➕ Send ElevenLabs API Key:")
    elif data == "admin_vkey_del":
        ADMIN_INPUT_STATE[user_id] = 'del_voice_key'
        keys = "\n".join([f"`{k}`" for k in get_all_voice_keys()])
        await q.edit_message_text(f"➖ Send Key to delete:\n\n{keys}", parse_mode=ParseMode.MARKDOWN)
    elif data == "admin_cast_ask":
        ADMIN_INPUT_STATE[user_id] = 'broadcast'
        await q.edit_message_text("📢 Send anything to Broadcast (Photo/Video/Text):")
    elif data == "admin_add_ask":
        ADMIN_INPUT_STATE[user_id] = 'add_money'
        await q.edit_message_text("💰 Format: `UserID Amount`")
    elif data == "admin_toggle_eco":
        set_economy_status(not get_economy_status())
        await admin_panel(update, context)
    elif data == "admin_back":
        await admin_panel(update, context)
    elif data == "admin_close":
        await q.message.delete()

# --- 3. INPUT HANDLER ---
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != str(OWNER_ID): return False

    state = ADMIN_INPUT_STATE.get(user_id)
    if not state: return False

    msg = update.message
    text = msg.text.strip() if msg.text else None

    # 🔥 CUSTOM TTS ID INPUT 🔥
    if state == 'set_tts_id' and text:
        set_custom_voice(text)
        await msg.reply_text(f"✅ **Custom Voice Set:** `{text}`")
        del ADMIN_INPUT_STATE[user_id]
        return True

    # 🔥 VOICE KEY INPUT 🔥
    if state == 'add_voice_key' and text:
        if add_voice_key(text): await msg.reply_text("✅ Voice Key Added!")
        else: await msg.reply_text("⚠️ Key already exists.")
        del ADMIN_INPUT_STATE[user_id]
        return True

    # 🔥 BROADCAST 🔥
    if state == 'broadcast':
        # logic for copying message to all users/groups
        await msg.reply_text("📢 Broadcasting...")
        del ADMIN_INPUT_STATE[user_id]
        return True

    # 🔥 MONEY 🔥
    if state == 'add_money' and text:
        try:
            uid, amt = map(int, text.split())
            update_balance(uid, amt)
            await msg.reply_text(f"✅ Added {amt} to {uid}")
        except: await msg.reply_text("❌ Format error.")
        del ADMIN_INPUT_STATE[user_id]
        return True

    return False
