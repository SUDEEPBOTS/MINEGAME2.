from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
# 🔥 Imports updated
from database import (
    groups_col, investments_col, users_col, 
    get_group_price, update_balance, check_registered, 
    register_user, get_user
)

# --- 1. WELCOME MESSAGE ---
async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.new_chat_members: return
    
    chat_title = update.effective_chat.title

    for member in update.message.new_chat_members:
        if member.id == context.bot.id: continue
        
        # 🔥 TUMHARA FORMAT
        await update.message.reply_text(
            f"👀 Hey {member.first_name} welcome to ゜{chat_title}"
        )

# --- 2. GLOBAL GROUP RANKING ---
async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Top 10 Groups by Activity
    top_groups_cursor = groups_col.find().sort("activity", -1).limit(10)
    top_groups = list(top_groups_cursor)

    if not top_groups:
        await update.message.reply_text("❌ Market abhi sunsaan hai! (No active groups)")
        return

    msg = "🏢 **GLOBAL MARKET RANKING** 🏢\n\n"
    rank = 1
    
    for grp in top_groups:
        name = grp.get("name", "Unknown Group")
        activity = grp.get("activity", 0)
        
        # Price Calculation Logic matches database.py
        price = round(10 + (activity * 0.1), 2)

        if rank == 1:
            msg += f"👑 **{name}**\n   🔥 Score: {activity} | 📈 Price: ₹{price}\n\n"
        else:
            msg += f"{rank}. **{name}**\n   🔥 Score: {activity} | 📈 Price: ₹{price}\n\n"
            
        rank += 1
    
    msg += "💡 _Tip: `/invest` in active groups to earn more!_"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# --- 3. MARKET INFO (Current Group) ---
async def market_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private": 
        await update.message.reply_text("❌ Ye command sirf Groups me chalti hai!")
        return
        
    price = get_group_price(chat.id)
    
    # Check total investment in this group
    total_invested_cursor = investments_col.aggregate([
        {"$match": {"group_id": chat.id}},
        {"$group": {"_id": None, "total": {"$sum": "$invested"}}}
    ])
    total_val = list(total_invested_cursor)
    market_cap = total_val[0]['total'] if total_val else 0
    
    await update.message.reply_text(
        f"📊 **MARKET STATUS: {chat.title}**\n\n"
        f"💰 **Share Price:** ₹{price}\n"
        f"🏦 **Market Cap:** ₹{market_cap}\n\n"
        f"🛒 Buy: `/invest <amount>`\n"
        f"💵 Sell: `/sell`\n"
        f"🏆 Top Investors: `/topinvest`", 
        parse_mode=ParseMode.MARKDOWN
    )

# --- 4. INVEST (Buy Shares) ---
async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private": 
        await update.message.reply_text("❌ Shares sirf Groups me khareed sakte ho!")
        return
    
    # Check Registration
    if not check_registered(user.id):
        register_user(user.id, user.first_name)
        
    try: 
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except: 
        await update.message.reply_text("⚠️ **Usage:** `/invest 100` (Amount likho)")
        return
        
    u_data = get_user(user.id)
    if u_data["balance"] < amount: 
        await update.message.reply_text(f"❌ **Garib!** Tere paas sirf ₹{u_data['balance']} hain.")
        return
    
    current_price = get_group_price(chat.id)
    shares = round(amount / current_price, 4) # 4 decimal places tak shares
    
    # 1. Paisa kaato
    update_balance(user.id, -amount)
    
    # 2. Investment Save karo
    investments_col.insert_one({
        "user_id": user.id, 
        "group_id": chat.id, 
        "shares": shares, 
        "invested": amount,
        "buy_price": current_price
    })
    
    await update.message.reply_text(
        f"✅ **INVESTMENT SUCCESSFUL!**\n\n"
        f"📉 **Amount:** ₹{amount}\n"
        f"📄 **Shares:** {shares}\n"
        f"📈 **Price:** ₹{current_price}/share",
        parse_mode=ParseMode.MARKDOWN
    )

# --- 5. SELL SHARES (Book Profit) ---
async def sell_shares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private": return
    
    # Find all shares of this user in this group
    invs = list(investments_col.find({"user_id": user.id, "group_id": chat.id}))
    if not invs: 
        await update.message.reply_text("❌ Is group me tumhare koi shares nahi hain!")
        return
    
    # Calculate Total
    total_shares = sum(i["shares"] for i in invs)
    current_price = get_group_price(chat.id)
    
    # Current Value
    payout = int(total_shares * current_price)
    
    # DB Updates
    investments_col.delete_many({"user_id": user.id, "group_id": chat.id})
    update_balance(user.id, payout)
    
    await update.message.reply_text(
        f"💵 **SHARES SOLD!**\n\n"
        f"📄 Sold: {round(total_shares, 2)} shares\n"
        f"💰 **Received:** ₹{payout}\n"
        f"📈 Rate: ₹{current_price}", 
        parse_mode=ParseMode.MARKDOWN
    )

# --- 6. 🔥 NEW: TOP INVESTORS (Group Specific) ---
async def top_investors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private": 
        await update.message.reply_text("❌ Group me use karo!")
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
        await update.message.reply_text("❌ Is group me abhi koi investor nahi hai.")
        return

    msg = f"🏆 **TOP INVESTORS: {chat.title}** 🏆\n\n"
    price = get_group_price(chat.id)
    
    for idx, item in enumerate(results, 1):
        uid = item["_id"]
        shares = item["total_shares"]
        value = int(shares * price)
        
        # User ka naam nikalo
        u_data = get_user(uid)
        name = u_data["name"] if u_data else "Unknown"
        
        msg += f"{idx}. **{name}**\n   📄 Shares: {round(shares, 1)} | 💰 Val: ₹{value}\n"
        
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
