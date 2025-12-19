from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import groups_col, investments_col, users_col, get_group_price, update_balance
from config import DEFAULT_BANNER

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Top 10 Groups
    top_groups_cursor = groups_col.find().sort("activity", -1).limit(10)
    top_groups = list(top_groups_cursor)

    if not top_groups:
        await update.message.reply_text("❌ Abhi koi data nahi hai!")
        return

    # 2. Caption Banao
    msg = "🏢 **TOP 10 GROUPS (Market)** 🏢\n\n"
    rank = 1
    for grp in top_groups:
        price = 10 + (grp.get("activity", 0) * 0.5)
        icon = "👑" if rank == 1 else f"{rank}."
        msg += f"{icon} **{grp['name']}**\n   🔥 Score: {grp.get('activity', 0)} | 📈 Price: ₹{price}\n\n"
        rank += 1
    
    msg += "💡 _Tip: Use /invest to buy shares!_"

    # 3. Top 1 Group ki DP lagao
    top_id = top_groups[0]["_id"]
    photo = DEFAULT_BANNER
    try:
        chat = await context.bot.get_chat(top_id)
        if chat.photo: photo = chat.photo.big_file_id
    except: pass

    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=msg, parse_mode=ParseMode.MARKDOWN)

async def market_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    gid = update.effective_chat.id
    price = get_group_price(gid)
    await update.message.reply_text(f"📊 **{update.effective_chat.title}**\n💰 Share Price: ₹{price}\n🛒 Buy: `/invest <amount>`\n💵 Sell: `/sell`", parse_mode=ParseMode.MARKDOWN)

async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; chat = update.effective_chat
    if chat.type == "private": await update.message.reply_text("❌ Group only!"); return
    try: amount = int(context.args[0])
    except: return
    u = users_col.find_one({"_id": user.id})
    if u["balance"] < amount: await update.message.reply_text("❌ Low Balance"); return
    
    price = get_group_price(chat.id); shares = amount / price
    update_balance(user.id, -amount)
    investments_col.insert_one({"user_id": user.id, "group_id": chat.id, "shares": shares, "invested": amount})
    await update.message.reply_text(f"✅ **Invested ₹{amount}**\n📈 Shares: {round(shares, 2)} @ ₹{price}")

async def sell_shares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; chat = update.effective_chat
    invs = list(investments_col.find({"user_id": user.id, "group_id": chat.id}))
    if not invs: await update.message.reply_text("❌ No Shares!"); return
    
    total_shares = sum(i["shares"] for i in invs)
    current_val = int(total_shares * get_group_price(chat.id))
    investments_col.delete_many({"user_id": user.id, "group_id": chat.id})
    update_balance(user.id, current_val)
    await update.message.reply_text(f"💵 **Sold Shares!**\n💰 Got: ₹{current_val}", parse_mode=ParseMode.MARKDOWN)
    
