import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
# 🔥 Imports updated
from database import (
    groups_col, investments_col, users_col, 
    get_group_price, update_balance, check_registered, 
    register_user, get_user
)

# Fancy Font Helper
def to_fancy(text):
    mapping = {'A': 'Λ', 'E': 'Є', 'S': 'δ', 'O': 'σ', 'T': 'ᴛ', 'N': 'ɴ', 'M': 'ᴍ', 'U': 'ᴜ', 'R': 'ʀ', 'D': 'ᴅ', 'C': 'ᴄ', 'P': 'ᴘ', 'G': 'ɢ', 'B': 'ʙ', 'L': 'ʟ', 'W': 'ᴡ', 'K': 'ᴋ', 'J': 'ᴊ', 'Y': 'ʏ', 'I': 'ɪ', 'H': 'ʜ'}
    return "".join(mapping.get(c.upper(), c) for c in text)

# --- 1. WELCOME MESSAGE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.new_chat_members: return
    
    chat_title = update.effective_chat.title

    for member in update.message.new_chat_members:
        if member.id == context.bot.id: continue
        
        # 🔥 FORMATTED MESSAGE
        msg_text = f"<blockquote>👀 Hey <b>{html.escape(member.first_name)}</b>, welcome to <b>゜{html.escape(chat_title)}</b></blockquote>"
        await update.message.reply_text(msg_text, parse_mode=ParseMode.HTML)

# --- 2. GLOBAL GROUP RANKING ---
async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Top 10 Groups by Activity
    top_groups_cursor = groups_col.find().sort("activity", -1).limit(10)
    top_groups = list(top_groups_cursor)

    if not top_groups:
        await update.message.reply_text("❌ Market is silent! (No active groups)", parse_mode=ParseMode.HTML)
        return

    msg = f"<blockquote><b>🏢 {to_fancy('GLOBAL MARKET RANKING')}</b></blockquote>\n\n"
    rank = 1
    
    for grp in top_groups:
        name = html.escape(grp.get("name", "Unknown Group"))
        activity = grp.get("activity", 0)
        
        # Price Calculation Logic
        price = round(10 + (activity * 0.1), 2)

        if rank == 1:
            msg += f"<blockquote>👑 <b>{name}</b>\n   🔥 Score: {activity} | 📈 Price: ₹{price}</blockquote>\n"
        else:
            msg += f"<blockquote><b>{rank}. {name}</b>\n   🔥 Score: {activity} | 📈 Price: ₹{price}</blockquote>\n"
            
        rank += 1
    
    msg += "\n💡 <i>Tip: <code>/invest</code> in active groups to earn more!</i>"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- 3. MARKET INFO (Current Group) ---
async def market_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private": 
        await update.message.reply_text("❌ This command works only in Groups!")
        return
        
    price = get_group_price(chat.id)
    
    # Check total investment in this group
    total_invested_cursor = investments_col.aggregate([
        {"$match": {"group_id": chat.id}},
        {"$group": {"_id": None, "total": {"$sum": "$invested"}}}
    ])
    total_val = list(total_invested_cursor)
    market_cap = total_val[0]['total'] if total_val else 0
    
    msg = f"""
<blockquote><b>📊 {to_fancy("MARKET STATUS")}: {html.escape(chat.title)}</b></blockquote>

<blockquote>
<b>💰 sʜᴀʀᴇ ᴘʀɪᴄᴇ :</b> ₹{price}
<b>🏦 ᴍᴀʀᴋᴇᴛ ᴄᴀᴘ :</b> ₹{market_cap}
</blockquote>

<blockquote>
<b>🛒 ʙᴜʏ :</b> <code>/invest [amount]</code>
<b>💵 sᴇʟʟ :</b> <code>/sell</code>
<b>🏆 ᴛᴏᴘ ɪɴᴠᴇsᴛᴏʀs :</b> <code>/topinvest</code>
</blockquote>
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- 4. INVEST (Buy Shares) ---
async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private": 
        await update.message.reply_text("❌ You can only buy shares in Groups!")
        return
    
    # Check Registration
    if not check_registered(user.id):
        register_user(user.id, user.first_name)
        
    try: 
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except: 
        await update.message.reply_text("⚠️ <b>Usage:</b> <code>/invest 100</code>", parse_mode=ParseMode.HTML)
        return
        
    u_data = get_user(user.id)
    if u_data["balance"] < amount: 
        await update.message.reply_text(f"❌ <b>Insufficient Funds!</b> You only have ₹{u_data['balance']}.", parse_mode=ParseMode.HTML)
        return
    
    current_price = get_group_price(chat.id)
    shares = round(amount / current_price, 4) 
    
    # 1. Deduct Money
    update_balance(user.id, -amount)
    
    # 2. Save Investment
    investments_col.insert_one({
        "user_id": user.id, 
        "group_id": chat.id, 
        "shares": shares, 
        "invested": amount,
        "buy_price": current_price
    })
    
    msg = f"""
<blockquote><b>✅ {to_fancy("INVESTMENT SUCCESSFUL")}</b></blockquote>

<blockquote>
<b>📉 ᴀᴍᴏᴜɴᴛ :</b> ₹{amount}
<b>📄 sʜᴀʀᴇs :</b> {shares}
<b>📈 ᴘʀɪᴄᴇ :</b> ₹{current_price}/share
</blockquote>
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- 5. SELL SHARES (Book Profit) ---
async def sell_shares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private": return
    
    # Find all shares of this user in this group
    invs = list(investments_col.find({"user_id": user.id, "group_id": chat.id}))
    if not invs: 
        await update.message.reply_text("❌ You don't have any shares in this group!")
        return
    
    # Calculate Total
    total_shares = sum(i["shares"] for i in invs)
    current_price = get_group_price(chat.id)
    
    # Current Value
    payout = int(total_shares * current_price)
    
    # DB Updates
    investments_col.delete_many({"user_id": user.id, "group_id": chat.id})
    update_balance(user.id, payout)
    
    msg = f"""
<blockquote><b>💵 {to_fancy("SHARES SOLD")}</b></blockquote>

<blockquote>
<b>📄 sᴏʟᴅ :</b> {round(total_shares, 2)} shares
<b>💰 ʀᴇᴄᴇɪᴠᴇᴅ :</b> ₹{payout}
<b>📈 ʀᴀᴛᴇ :</b> ₹{current_price}
</blockquote>
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- 6. TOP INVESTORS (Group Specific) ---
async def top_investors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private": 
        await update.message.reply_text("❌ Use this in a Group!")
        return

    # Aggregation to sum shares per user in this group
    pipeline = [
        {"$match": {"group_id": chat.id}},
        {"$group": {"_id": "$user_id", "total_shares": {"$sum": "$shares"}}},
        {"$sort": {"total_shares": -1}},
        {"$limit": 10}
    ]
    
    results = list(investments_col.aggregate(pipeline))
    
    if not results:
        await update.message.reply_text("❌ No investors in this group yet.")
        return

    msg = f"<blockquote><b>🏆 {to_fancy('TOP INVESTORS')}: {html.escape(chat.title)}</b></blockquote>\n\n"
    price = get_group_price(chat.id)
    
    for idx, item in enumerate(results, 1):
        uid = item["_id"]
        shares = item["total_shares"]
        value = int(shares * price)
        
        # User Name
        u_data = get_user(uid)
        name = html.escape(u_data["name"]) if u_data else "Unknown"
        
        msg += f"<blockquote><b>{idx}. {name}</b>\n   📄 Shares: {round(shares, 1)} | 💰 Val: ₹{value}</blockquote>\n"
        
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
