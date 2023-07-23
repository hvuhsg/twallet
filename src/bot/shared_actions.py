from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .messages import RECEIPT


async def show_wallet_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_balance = context.user_data["wallet"].balance

    # Prepare the inline keyboard
    keyboard = [
        [InlineKeyboardButton("➡️ Send", callback_data="send"), InlineKeyboardButton("➕ Receive", callback_data="receive")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show the wallet balance and options
    await context.user_data["msg"].edit_text(
        text=f"💰 My Wallet\n\nWallet balance: <code>{wallet_balance}</code> TON",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )


async def send_receipt(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    # Implement the logic to send the cryptocurrency to the recipient
    send_amount = float(context.user_data['send_amount'])
    send_fee = float(context.user_data['send_fee'])
    send_address = context.user_data['send_address']
    send_total = round(send_amount + send_fee, 4)

    await context.user_data["wallet"].transfer(send_amount, send_address, comment="todo-comment")

    await context.bot.send_message(
        chat_id,
        RECEIPT.format(amount=send_amount, fee=send_fee, total=send_total, address=send_address),
        parse_mode=ParseMode.HTML,
    )
    new_message = await context.bot.send_message(chat_id, ".")
    old_msg = context.user_data["msg"]
    context.user_data["msg"] = new_message
    await old_msg.delete()
