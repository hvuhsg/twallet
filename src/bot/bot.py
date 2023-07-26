import logging
import os
from uuid import uuid4
from secrets import token_urlsafe

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    PicklePersistence,
    InlineQueryHandler,
)
from telegram.constants import ParseMode

from .handlers import handlers, start


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Replace 'YOUR_TOKEN' with your actual Telegram bot token
TOKEN = os.environ["BOT_TOKEN"]


# Setup persistence
persistence = PicklePersistence(filepath="../data.db")


# Handler for handling user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data['state']
    await update.message.delete()

    func = handlers.get(state)
    next_state = await func(update, context)
    context.user_data["state"] = next_state


# Handler for handling inline keyboard button clicks
async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    func = handlers.get(query.data)
    next_state = await func(update, context)
    context.user_data["state"] = next_state


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query

    if not query:  # empty query should not be handled
        return

    wallet = context.user_data.get("wallet")
    if not wallet:
        print("No Wallet")
        await update.inline_query.answer([])
        return

    await wallet.load_state()

    try:
        amount = float(query)
    except ValueError:
        print("Error parse amount")
        await update.inline_query.answer([])
        return

    if wallet.balance < amount:
        print("Low balance")
        await update.inline_query.answer([])
        return

    transfer_uuid = token_urlsafe(16)
    if "transfers" not in context.bot_data:
        context.bot_data["transfers"] = {}
    context.bot_data["transfers"][transfer_uuid] = {"wallet": wallet, "amount": amount}

    reply_markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                f"Claim {amount} TON",
                url=f"https://t.me/TONPrivateWalletBot?start=accept-{transfer_uuid}",
            )
        ]]
    )
    message = InputTextMessageContent(message_text=f"Cheque for <b>{amount}</b> TON", parse_mode=ParseMode.HTML)

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"Create a cheque: {amount} TON",
            description=f"Available: {wallet.balance} TON",
            input_message_content=message,
            reply_markup=reply_markup,
        ),
    ]

    await update.inline_query.answer(results, cache_time=8)


# Create the Telegram bot
def main():
    """Start the bot."""
    application = Application.builder().token(TOKEN).persistence(persistence).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_inline_buttons))
    application.add_handler(InlineQueryHandler(inline_query))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
