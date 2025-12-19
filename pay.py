import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import (
    update_balance, get_balance, get_user, 
    set_protection, is_protected, get_economy_status, 
    update_kill_count, set_dead, is_dead
)

# --- ECONOMY CONFIGS ---
PROTECT_COST = 5000   # 1 Day protection
HOSPITAL_FEE = 5000   # Zinda hone ka kharcha
ROB_FAIL_PENALTY = 500 

# --- 1. PAY (Transfer Money) ---
async def pay_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 **Economy is OFF!**")
    
    sender = update.effective_user
    if is_dead(sender.id): return await update.message.reply_text("👻 **Tu mara hua hai!**\nPehle hospital ja kar ilaaj karwa.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply karke likho: `/pay 100`")
    
    receiver = update.message.reply_to_message.from_user
    if sender.id == receiver.id: return await update.message.reply_text("❌ Khud ko nahi bhej sakte!")
    if receiver.is_bot: return await update.message.reply_text("❌ Bot ko paisa doge?")

    try: amount = int(context.args[0])
    except: return await update.message.reply_text("⚠️ Usage: `/pay 100`")
    
    if amount <= 0: return await update.message.reply_text("❌ Sahi amount daal!")
    if get_balance(sender.id) < amount: return await update.message.reply_text("❌ Paisa nahi hai tere paas!")
    
    update_balance(sender.id, -amount)
    update_balance(receiver.id, amount)
    
    await update.message.reply_text(f"💸 **Transfer Successful!**\n👤 {sender.first_name} sent ₹{amount} to {receiver.first_name}.")
    
    # Notify Receiver in DM
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
    
    if is_dead(user.id): return await update.message.reply_text("👻 **Tu mara hua hai!** Dead body ko shield nahi milti.")

    if get_balance(user.id) < PROTECT_COST:
        return await update.message.reply_text(f"❌ Protection ke liye ₹{PROTECT_COST} chahiye!")
        
    if is_protected(user.id):
        return await update.message.reply_text("🛡️ Tu pehle se Protected hai!")
    
    update_balance(user.id, -PROTECT_COST)
    set_protection(user.id, 24) # 24 Hours
    
    await update.message.reply_text(f"🛡️ **Shield Activated!**\n₹{PROTECT_COST} kate. Ab 24 ghante tak koi Rob/Kill nahi kar payega.")

# --- 3. ROB (Chori) ---
async def rob_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 Economy OFF.")
    
    thief = update.effective_user
    if is_dead(thief.id): return await update.message.reply_text("👻 Bhoot chori nahi kar sakte!")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Kisko lootna hai? Reply command on message.")
    
    victim = update.message.reply_to_message.from_user
    if thief.id == victim.id: return
    
    if is_dead(victim.id): return await update.message.reply_text("☠️ **Wo already dead hai!** Laash se kya lootega?")
    
    # Checks
    if is_protected(victim.id):
        return await update.message.reply_text(f"🛡️ **Fail!** {victim.first_name} ne Protection le rakhi hai!")
    
    victim_bal = get_balance(victim.id)
    if victim_bal < 100:
        return await update.message.reply_text("❌ Is bhikari ke paas kuch nahi hai!")

    # Luck System (40% Chance Pass)
    if random.random() < 0.4:
        # Success
        loot = int(victim_bal * random.uniform(0.1, 0.4)) 
        update_balance(victim.id, -loot)
        update_balance(thief.id, loot)
        
        # Group Message
        await update.message.reply_text(f"🔫 **ROBBERY SUCCESS!**\nTune {victim.first_name} ke ₹{loot} uda liye! 🏃‍♂️💨")
        
        # 🔥 DM ALERT TO VICTIM
        try:
            await context.bot.send_message(
                chat_id=victim.id,
                text=f"⚠️ **ALERT: ROBBERY!**\n\n🕵️‍♂️ **{thief.first_name}** ne tumhe loot liya!\n📉 Amount Stolen: ₹{loot}\n💡 Tip: Use /bank to save money.",
                parse_mode=ParseMode.MARKDOWN
            )
        except: pass

    else:
        # Fail & Penalty
        update_balance(thief.id, -ROB_FAIL_PENALTY)
        await update.message.reply_text(f"👮 **POLICE AA GAYI!**\nChori pakdi gayi. Fine: ₹{ROB_FAIL_PENALTY}")

# --- 4. KILL (Free Cost + Reward + Dead Status) ---
async def kill_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not get_economy_status(): return await update.message.reply_text("🔴 Economy OFF.")
    
    killer = update.effective_user
    if is_dead(killer.id): return await update.message.reply_text("👻 **Tu khud dead hai!** Pehle revive ho.")

    if not update.message.reply_to_message: return await update.message.reply_text("⚠️ Reply karke `/kill` likho.")
    
    victim = update.message.reply_to_message.from_user
    if killer.id == victim.id: return await update.message.reply_text("❌ Khud ko kyu maar raha hai?")
    
    # Check if victim is already dead
    if is_dead(victim.id):
        return await update.message.reply_text(f"☠️ **User Already Dead!**\n{victim.first_name} pehle se mara hua hai. Laash ko aur kitna maaroge?")

    # Protection Check
    if is_protected(victim.id):
        return await update.message.reply_text(f"🛡️ **Mission Fail!** {victim.first_name} protected hai.")

    # 3. Transaction Logic
    # No Cost for Killer (Free Kill)
    
    # Victim loses 50%
    victim_bal = get_balance(victim.id)
    loss = int(victim_bal * 0.5) 
    update_balance(victim.id, -loss)
    
    # 🔥 REWARD: Killer gets loot
    bounty = int(loss * 0.5)
    update_balance(killer.id, bounty)
    
    # 🔥 SET TARGET DEAD
    set_dead(victim.id, True)
    update_kill_count(killer.id)
    
    # Medical Button Logic
    kb = [[InlineKeyboardButton(f"🏥 Medical Revive (₹{HOSPITAL_FEE})", callback_data=f"revive_{victim.id}")]]
    
    # Group Message
    await update.message.reply_text(
        f"💀 **MURDER!**\n"
        f"🔪 **Killer:** {killer.first_name}\n"
        f"🩸 **Victim:** {victim.first_name} (DIED)\n"
        f"💰 **Loot:** Killer stole ₹{bounty}!\n\n"
        f"🚑 **{victim.first_name} is now DEAD!**\n"
        f"Game khelne ke liye niche button daba kar revive ho jao.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

    # 🔥 DM ALERT TO VICTIM
    try:
        await context.bot.send_message(
            chat_id=victim.id,
            text=f"☠️ **YOU ARE KILLED!**\n\n🔪 **{killer.first_name}** murdered you.\n📉 You lost: ₹{loss}\n\n🏥 **Revive:** Group me 'Medical Revive' button dabao wapis zinda hone ke liye.",
            parse_mode=ParseMode.MARKDOWN
        )
    except: pass

# --- 5. REVIVE HANDLER (Button Click) ---
async def revive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user = q.from_user
    data = q.data
    
    # Check if button is for this user
    target_id = int(data.split("_")[1])
    if user.id != target_id:
        return await q.answer("Ye tumhari laash nahi hai! 😠", show_alert=True)
        
    if not is_dead(user.id):
        return await q.answer("Tum pehle se zinda ho!", show_alert=True)
        
    if get_balance(user.id) < HOSPITAL_FEE:
        return await q.answer(f"❌ Doctor ki fees ₹{HOSPITAL_FEE} hai! Paise kama ke aao.", show_alert=True)
        
    # Transaction
    update_balance(user.id, -HOSPITAL_FEE)
    set_dead(user.id, False)
    
    await q.edit_message_text(
        f"🏥 **REVIVED SUCCESSFUL!**\n\n"
        f"👤 {user.first_name} ab wapis zinda hai!\n"
        f"💸 Hospital Bill: ₹{HOSPITAL_FEE} paid.\n"
        f"Ab jao badla lo! ⚔️"
    )

# --- 6. ALIVE / STATUS ---
async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if is_dead(user.id):
        status = "☠️ **DEAD** (Use Medical)"
    elif is_protected(user.id):
        status = "🛡️ **PROTECTED**"
    else:
        status = "⚠️ **VULNERABLE**"
        
    bal = get_balance(user.id)
    await update.message.reply_text(f"👤 **STATUS REPORT:**\n\n💰 Money: ₹{bal}\n❤️ Condition: {status}", parse_mode=ParseMode.MARKDOWN)
    
