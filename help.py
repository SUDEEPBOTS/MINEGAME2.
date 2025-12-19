from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 **COMMAND LIST**\n\n"
        "🎮 **GAME:**\n"
        "`/bet <amount>` - Game khelo (e.g. /bet 100)\n"
        "`/balance` - Apna paisa check karo\n\n"
        
        "📈 **MARKET & GROUP:**\n"
        "`/ranking` - Top 10 Groups Image ke saath\n"
        "`/market` - Group ka Share Price dekho\n"
        "`/invest <amount>` - Group me paisa lagao\n"
        "`/sell` - Shares bech kar profit lo\n\n"
        
        "🛒 **SHOP:**\n"
        "`/shop` - Titles khareedo\n"
        "`/redeem <code>` - Promo code use karo"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
  
