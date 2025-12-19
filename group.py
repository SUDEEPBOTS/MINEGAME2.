from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import groups_col, get_group_price

# Default Banner agar Top Group ki photo na ho
DEFAULT_BANNER = "https://i.ibb.co/vzDpQx9/ranking-banner.jpg"

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Top 10 Groups nikalo
    top_groups_cursor = groups_col.find().sort("activity", -1).limit(10)
    top_groups = list(top_groups_cursor) # List me convert kiya taaki index use kar sakein

    if not top_groups:
        await update.message.reply_text("❌ Abhi koi data nahi hai!")
        return

    # 2. Ranking List (Caption) Banao
    msg = "🏆 **OFFICIAL GROUP RANKING** 🏆\n\n"
    rank = 1
    
    for grp in top_groups:
        price = 10 + (grp.get("activity", 0) * 0.5)
        # Icons decoration
        if rank == 1: icon = "👑"
        elif rank == 2: icon = "🥈"
        elif rank == 3: icon = "🥉"
        else: icon = f"{rank}."
        
        # Format: 👑 Name | 🔥 Score | 📈 Price
        msg += f"{icon} **{grp['name']}**\n   🔥 Score: {grp.get('activity', 0)} | 📈 Share: ₹{price}\n\n"
        rank += 1
    
    msg += "💡 _Tip: `/invest` in rising groups to earn profit!_"

    # 3. Top 1 Group ki Photo Dhoondo
    top_group_id = top_groups[0]["_id"] # Rank 1 wale ki ID
    photo_to_send = DEFAULT_BANNER # Pehle default maan ke chalo

    try:
        # Telegram API se Top Group ki chat info nikalo
        chat_info = await context.bot.get_chat(top_group_id)
        if chat_info.photo:
            # Agar photo hai, toh uska File ID lelo
            photo_to_send = chat_info.photo.big_file_id
    except:
        # Agar bot us group se kick ho gaya ya error aya, toh default rehne do
        pass

    # 4. Photo aur Caption bhejo
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo_to_send,
        caption=msg,
        parse_mode=ParseMode.MARKDOWN
    )

# ... (Baki market_info, invest, sell function wahi purane rahenge) ...
