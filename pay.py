import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import (
    update_balance, get_balance, get_user, 
    set_protection, is_protected, get_economy_status, 
    update_kill_count, set_dead, is_dead,
    check_registered, register_user
)

# --- ECONOMY CONFIGS ---
PROTECT_COST = 5000   # 1 Day protection
HOSPITAL_FEE = 5000   # Instant Revive Cost
ROB_FAIL_PENALTY = 500 
KILL_REWARD = 900     
AUTO_REVIVE_TIME = 1800 # 🔥 30 Minutes (in Seconds)

# --- HELPER: REGISTER BUTTON ---
async def send_register_button(update):
    user = update.effective_user
    kb = [[InlineKeyboardButton("📝 Register Now", callback_data=f"reg_start_{user.id}")]]
    await update.message.reply_text(
        f"🛑 **{user.first_name}, Register First!**\nGame khelne ke liye register karna zaroori hai.",
        reply_markup=InlineKeyboardMarkup(kb),
        quote=True
    )

# --- 🔥 AUTO REVIVE JOB (Background Task) ---
async def auto_revive_job(context: ContextTypes.DEFAULT_TYPE):
    """Ye function 30 min baad chalega"""
    user_id = context.job.data
    
    # Check karo agar wo abhi bhi dead hai (kisi ne pay karke revive na kiya ho)
    if is_dead(user_id):
        set_dead(user_id, False) # Database me zinda kar do
        
        # User ko DM bhej do (Optional, hata bhi sakte ho agar full silent chahiye)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✨ **Miracle!**\n30 minute pure ho gaye. Tum automatically **Zinda** ho gaye ho! 🧘‍♂️",
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass

# --- 1. PAY (Transfer Money) ---
async def pay_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 **Economy is OFF!**")
    
    sender = update.effective_user
    
    if not check_registered(sender.id):
        await send_register_button(update)
        return

    if is_dead(sender.id): return await update.message.reply_text("👻 **Tu mara hua hai!**\nPehle hospital ja kar ilaaj karwa ya 30 min wait kar.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply karke likho: `/pay 100`")
    
    receiver = update.message.reply_to_message.from_user
    
    if receiver.is_bot: return await update.message.reply_text("❌ Bot ko paisa nahi bhej sakte!")
    if sender.id == receiver.id: return await update.message.reply_text("❌ Khud ko nahi bhej sakte!")

    if not check_registered(receiver.id):
        return await update.message.reply_text(f"❌ **Fail!** {receiver.first_name} registered nahi hai.")

    try: amount = int(context.args[0])
    except: return await update.message.reply_text("⚠️ Usage: `/pay 100`")
    
    if amount <= 0: return await update.message.reply_text("❌ Sahi amount daal!")
    if get_balance(sender.id) < amount: return await update.message.reply_text("❌ Paisa nahi hai tere paas!")
    
    update_balance(sender.id, -amount)
    update_balance(receiver.id, amount)
    
    await update.message.reply_text(f"💸 **Transfer Successful!**\n👤 {sender.first_name} sent ₹{amount} to {receiver.first_name}.")
    
    try:
        await context.bot.send_message(
            chat_id=receiver.id, 
            text=f"🏧 **RECEIVED MONEY!**\n\n👤 {sender.first_name} ne tumhe ₹{amount} bheje hain.",
            parse_mode=ParseMode.MARKDOWN
        )
    except: pass

# --- 2. PROTECT (Shield) ---
async def protect_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 Economy OFF.")
    user = update.effective_user
    
    if not check_registered(user.id):
        await send_register_button(update)
        return
    
    if is_dead(user.id): return await update.message.reply_text("👻 **Tu mara hua hai!** Dead body ko shield nahi milti.")

    if get_balance(user.id) < PROTECT_COST:
        return await update.message.reply_text(f"❌ Protection ke liye ₹{PROTECT_COST} chahiye!")
        
    if is_protected(user.id):
        return await update.message.reply_text("🛡️ Tu pehle se Protected hai!")
    
    update_balance(user.id, -PROTECT_COST)
    set_protection(user.id, 24) 
    
    await update.message.reply_text(f"🛡️ **Shield Activated!**\n₹{PROTECT_COST} kate. Ab 24 ghante tak koi Rob/Kill nahi kar payega.")

# --- 3. ROB (Chori) ---
async def rob_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 Economy OFF.")
    
    thief = update.effective_user
    
    if not check_registered(thief.id):
        await send_register_button(update)
        return

    if is_dead(thief.id): return await update.message.reply_text("👻 Bhoot chori nahi kar sakte!")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Kisko lootna hai? Reply command on message.")
    
    victim = update.message.reply_to_message.from_user
    
    if victim.is_bot: return await update.message.reply_text("👮 **Bot Police Bula Lega!** Use nahi loot sakte.")
    if thief.id == victim.id: return await update.message.reply_text("❌ Khud ki jeb katega?")
    
    if not check_registered(victim.id):
        return await update.message.reply_text(f"⚠️ **Fail!** {victim.first_name} registered nahi hai (Gareeb hai).")

    if is_dead(victim.id): return await update.message.reply_text("☠️ Laash se kya lootega?")
    
    if is_protected(victim.id):
        return await update.message.reply_text(f"🛡️ **Fail!** {victim.first_name} Protected hai!")
    
    victim_bal = get_balance(victim.id)
    if victim_bal < 100:
        return await update.message.reply_text("❌ Is bhikari ke paas kuch nahi hai!")

    if random.random() < 0.4:
        # Success
        loot = int(victim_bal * random.uniform(0.1, 0.4)) 
        update_balance(victim.id, -loot)
        update_balance(thief.id, loot)
        
        await update.message.reply_text(f"🔫 **ROBBERY SUCCESS!**\nTune {victim.first_name} ke ₹{loot} uda liye! 🏃‍♂️💨")
        
        try:
            await context.bot.send_message(
                chat_id=victim.id,
                text=(f"⚠️ **YOU WERE ROBBED!**\nRobber: 👤 {thief.first_name}\nLost: ₹{loot}\nUse `/bank` to save money!")
            )
        except Exception: pass

    else:
        update_balance(thief.id, -ROB_FAIL_PENALTY)
        await update.message.reply_text(f"👮 **POLICE AA GAYI!**\nChori pakdi gayi. Fine: ₹{ROB_FAIL_PENALTY}")


# --- 4. KILL (Free Cost + Fixed Reward + AUTO REVIVE) ---
async def kill_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 Economy OFF.")
    
    killer = update.effective_user
    
    if not check_registered(killer.id):
        await send_register_button(update)
        return

    if is_dead(killer.id): return await update.message.reply_text("👻 **Tu khud dead hai!**")

    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke `/kill` likho.")
    
    victim = update.message.reply_to_message.from_user
    
    if victim.is_bot: return await update.message.reply_text("🤖 **SYSTEM ERROR:** Main Amar hu! Mujhe koi nahi maar sakta.")
    if killer.id == victim.id: return await update.message.reply_text("❌ Suicide mat kar bhai, life precious hai! ❤️")
    
    if not check_registered(victim.id):
        register_user(victim.id, victim.first_name)
    
    if is_dead(victim.id):
        return await update.message.reply_text(f"☠️ **Already Dead!**\n{victim.first_name} pehle se mara hua hai.")

    if is_protected(victim.id):
        return await update.message.reply_text(f"🛡️ **Fail!** {victim.first_name} Protected hai.")

    # Kill Logic
    victim_bal = get_balance(victim.id)
    if victim_bal > 0:
        loss = int(victim_bal * 0.5)
        update_balance(victim.id, -loss)
    
    update_balance(killer.id, KILL_REWARD)
    
    set_dead(victim.id, True)
    update_kill_count(killer.id)
    
    # 🔥 SCHEDULE AUTO REVIVE (30 Mins Timer)
    context.job_queue.run_once(auto_revive_job, AUTO_REVIVE_TIME, data=victim.id)
    
    kb = [[InlineKeyboardButton(f"🏥 Instant Revive (₹{HOSPITAL_FEE})", callback_data=f"revive_{victim.id}")]]
    
    await update.message.reply_text(
        f"💀 **MURDER!**\n"
        f"🔪 **Killer:** {killer.first_name}\n"
        f"🩸 **Victim:** {victim.first_name} (DIED)\n"
        f"💰 **Bounty:** Killer got ₹{KILL_REWARD}!\n"
        f"⏳ **Note:** Victim 30 mins mein apne aap zinda ho jayega.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

    try:
        await context.bot.send_message(
            chat_id=victim.id,
            text=(f"⚠️ **You were killed!**\nKiller: 👤 {killer.first_name}\nStatus: ☠️ DEAD\n\n💡 Tum 30 min baad automatic zinda ho jaoge, ya fir hospital fees bhar ke abhi ho sakte ho.")
        )
    except Exception: pass

# --- 5. REVIVE HANDLER ---
async def revive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user = q.from_user
    data = q.data
    
    target_id = int(data.split("_")[1])
    
    if not check_registered(user.id):
        return await q.answer("Pehle /start karke register karo!", show_alert=True)

    if user.id != target_id:
        return await q.answer("Ye tumhari laash nahi hai! 😠", show_alert=True)
        
    if not is_dead(user.id):
        return await q.answer("Tum pehle se zinda ho!", show_alert=True)
        
    if get_balance(user.id) < HOSPITAL_FEE:
        return await q.answer(f"❌ Doctor ki fees ₹{HOSPITAL_FEE} hai! Paise nahi hain to 30 min wait karo.", show_alert=True)
        
    update_balance(user.id, -HOSPITAL_FEE)
    set_dead(user.id, False)
    
    await q.edit_message_text(
        f"🏥 **REVIVED SUCCESSFUL!**\n\n"
        f"👤 {user.first_name} ne paise dekar ilaaj karwa liya!\n"
        f"💸 Hospital Bill: ₹{HOSPITAL_FEE} paid.\n"
        f"Ab jao badla lo! ⚔️"
    )

# --- 6. ALIVE / STATUS ---
async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not check_registered(user.id):
        await send_register_button(update)
        return
    
    if is_dead(user.id):
        status = "☠️ **DEAD** (Reviving in 30m)"
    elif is_protected(user.id):
        status = "🛡️ **PROTECTED**"
    else:
        status = "⚠️ **VULNERABLE**"
        
    bal = get_balance(user.id)
    await update.message.reply_text(f"👤 **STATUS REPORT:**\n\n💰 Money: ₹{bal}\n❤️ Condition: {status}", parse_mode=ParseMode.MARKDOWN)
    
