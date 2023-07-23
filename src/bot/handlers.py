import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .messages import WALLET_ADDRESS, SEND_AMOUNT, SEND_ADDRESS, SEND_CONFIRM, SETTINGS, LOGIN, INVALID_ADDRESS, WELCOME_MESSAGE
from .shared_actions import show_wallet_options, send_receipt
from .helpers import create_password_hash, is_password_valid

from wallet.wallet import Wallet
from wallet.utils import validate_address, to_ton


async def deeplink_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arg = context.user_data["redirect-args"].removeprefix("/start ")
    action_key = arg.split("-")[0]

    func = deeplink_handlers.get(action_key)
    if not func:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("< Wallet", callback_data="back")]])
        context.user_data["msg"].edit_text("⚠️ Invalid Link", reply_markup=reply_markup)
        return

    result = await func(update, context)
    return result


async def send_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /start=transfer-address_<address>-amount_<amount>-comment_<comment>
    arg = context.user_data["redirect-args"].removeprefix("/start ")
    action_values = arg.split("-")[1:]
    data = {
        value_pair.split('_')[0]: value_pair.split('_')[1]
        for value_pair in action_values
    }

    context.user_data["send_address"] = data["address"]
    context.user_data["send_amount"] = to_ton(int(data["amount"]))
    context.user_data["send_comment"] = data["comment"]

    return await send_amount_handler(update, context, amount=context.user_data["send_amount"])


async def accept_transfer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /start=accept-<transfer uuid>
    arg = context.user_data["redirect-args"].removeprefix("/start ")
    transfer_uuid = arg.split("-")[1:]
    transfer_data = context.bot_data.get("transfers", {}).get(transfer_uuid)

    if transfer_data is None:
        await update.message.reply_text("⚠️ transfer was redeemed or canceled")
        return

    self_wallet = context.user_data["wallet"]
    wallet = transfer_data["wallet"]
    amount = transfer_data["amount"]

    if self_wallet.balance < amount:
        await update.message.reply_text("⚠️ The sender does not have sufficient funds on his balance")
        return

    try:
        await wallet.transfer(amount=amount, address=self_wallet.address, comment="contact-transfer")
    except:
        await update.message.reply_text("⚠️ Unknown error during transfer of funds")
        return

    await update.message.reply_text(f"✅ You’ve received: {amount} TON")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    has_args = update.message.text != "/start"

    if has_args:
        context.user_data["redirect-args"] = update.message.text

        if "wallet" in context.user_data:
            context.user_data["state"] = await deeplink_handler(update, context)
            await update.message.delete()
            return
        else:
            context.user_data["redirect"] = "deeplink"

    password_data = context.user_data.get("password")

    if password_data:
        # Request a login password
        message = await update.message.reply_text(LOGIN, parse_mode=ParseMode.HTML)
        context.user_data["state"] = 'check-password'
    else:
        # If the user is new, request a password to create the wallet
        message = await update.message.reply_text(WELCOME_MESSAGE, parse_mode=ParseMode.HTML)
        context.user_data["settings"] = {"language": "English", "currency": "USD"}
        context.user_data["state"] = 'new-password'

    context.user_data["msg"] = message
    await update.message.delete()


async def new_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Save password hash
    password = update.message.text
    password_hash, password_salt = create_password_hash(password)
    context.user_data['prepassword'] = {"hash": password_hash, "salt": password_salt}
    await context.user_data["msg"].edit_text("Please send the password again:")

    return "confirm_password"


async def check_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password_data = context.user_data["password"]
    password = update.message.text
    if is_password_valid(password, password_data["hash"], password_data["salt"]):
        context.user_data["last_login"] = datetime.datetime.now()

        # Load wallet
        wallet = Wallet.from_password(password)
        await wallet.load_state()
        context.user_data["wallet"] = wallet

        if redirect_state := context.user_data.get("redirect"):
            context.user_data.pop("redirect")
            func = handlers[redirect_state]
            await func(update, context)
        else:
            await show_wallet_options(update, context)
    else:
        await context.user_data["msg"].edit_text("Invalid Password!.\nPlease enter your password:")
        return "check-password"


async def confirm_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password_data = context.user_data["prepassword"]
    password = update.message.text
    if is_password_valid(password, password_data["hash"], password_data["salt"]):
        context.user_data.pop("prepassword")
        context.user_data["password"] = password_data

        # Create wallet
        effective_password = f"{password} {update.effective_user.id}"
        wallet = Wallet.from_password(effective_password)
        await wallet.load_state()
        try:
            await wallet.initialize()
        except:
            pass

        context.user_data["wallet"] = wallet
        context.user_data["last_login"] = datetime.datetime.now()

        # await context.bot.set_chat_menu_button(
        #     update.effective_chat.id,
        #     MenuButtonWebApp("Wallet", WebAppInfo("https://t.me/TONPrivateWalletBot/Wallet")),
        # )

        if redirect_state := context.user_data.get("redirect"):
            context.user_data.pop("redirect")
            func = handlers[redirect_state]
            return await func(update, context)
        else:
            return await show_wallet_options(update, context)
    else:
        await context.user_data["msg"].edit_text("Passwords did not match.\nPlease choose a password:")
        return "new-password"


async def send_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    if not validate_address(address):
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Cancel", callback_data="cancel-send")]]
        )
        try:
            await context.user_data["msg"].edit_text(INVALID_ADDRESS, reply_markup=reply_markup)
        except BadRequest:
            pass
        return "send-address"

    context.user_data['send_address'] = address

    fee = 0.05
    context.user_data["send_fee"] = fee
    min_send = 0.001
    balance = context.user_data["wallet"].balance

    # Prepare the inline keyboard
    keyboard = [
        [InlineKeyboardButton(f"Min: {min_send}", callback_data="min_send"), InlineKeyboardButton(f"Max: {balance-fee}", callback_data="max_send")],
        [InlineKeyboardButton("Cancel", callback_data="cancel-send")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.user_data["msg"].edit_text(
        SEND_AMOUNT.format(fee=fee, min_amount=min_send, max_amount=balance),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )

    return "send_amount"


async def send_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float = None):
    if amount is None:
        context.user_data['send_amount'] = update.message.text
    else:
        context.user_data['send_amount'] = amount

    balance = context.user_data["wallet"].balance
    send_address = context.user_data['send_address']
    send_amount = float(context.user_data['send_amount'])
    fee = 0.05
    total_amount = send_amount + fee
    balance_after = balance - total_amount

    # Prepare the inline keyboard with 'Send' and 'Cancel' buttons
    keyboard = [
        [
            InlineKeyboardButton("✅Yes", callback_data="send-confirm"),
            InlineKeyboardButton("❌No", callback_data="cancel-send")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show the send details and options
    await context.user_data["msg"].edit_text(
        text=SEND_CONFIRM.format(
            address=send_address,
            amount=send_amount,
            fee=fee,
            total_amount=round(total_amount, 5),
            balance_after=round(balance_after, 5),
        ),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )


async def send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Prepare the inline keyboard
    keyboard = [
        [InlineKeyboardButton("Send to Contact", switch_inline_query=" ")],
        [InlineKeyboardButton("Cancel", callback_data="cancel-send")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.user_data["msg"].edit_text(SEND_ADDRESS, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    return 'send-address'


async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_wallet_options(update, context)


async def send_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if datetime.datetime.now() - context.user_data["last_login"] < datetime.timedelta(minutes=1):
        chat_id = update.effective_chat.id

        # Implement the logic to send the cryptocurrency to the recipient
        send_amount = float(context.user_data['send_amount'])
        send_address = context.user_data['send_address']
        comment = context.user_data.pop("send-comment", "todo-comment")

        await context.user_data["wallet"].transfer(send_amount, send_address, comment=comment)
        await context.user_data["wallet"].load_state()

        await send_receipt(chat_id, context)
        await show_wallet_options(update, context)
    else:
        # Login again before display
        await context.user_data["msg"].edit_text(LOGIN, parse_mode=ParseMode.HTML)
        context.user_data["redirect"] = "send-confirm"
        return 'check-password'


async def cancel_send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_wallet_options(update, context)


async def reactive_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = context.user_data['wallet'].address

    # Prepare the inline keyboard with a back button
    keyboard = [[InlineKeyboardButton("< Back", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show the wallet address and options
    await context.user_data["msg"].edit_text(
        text=WALLET_ADDRESS.format(address=wallet_address),
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def min_send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = 0.001
    await send_amount_handler(update, context, amount=amount)


async def max_send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fee = 0.05
    amount = float(context.user_data["wallet"].balance) - fee
    await send_amount_handler(update, context, amount=amount)


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = context.user_data["settings"]["language"]
    currency = context.user_data["settings"]["currency"]

    keyboard = [
        # [InlineKeyboardButton(text="Change language", callback_data="settings-language")],
        # [InlineKeyboardButton(text="Change local currency", callback_data="settings-currency")],
        [InlineKeyboardButton(text="Display 24 words", callback_data="wordlist")],
        [InlineKeyboardButton(text="< Back", callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.user_data["msg"].edit_text(
        SETTINGS,
        reply_markup=reply_markup,
    )


async def change_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(text="🇺🇸 English", callback_data="set-language-english"),
            InlineKeyboardButton(text="🇮🇱 Hebrew", callback_data="set-language-hebrew"),
        ],
        [
            InlineKeyboardButton(text="< Back", callback_data="settings"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await context.user_data["msg"].edit_text("Please, select a language", reply_markup=reply_markup)


async def change_currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(text="USD", callback_data="set-currency-usd"),
            InlineKeyboardButton(text="ILS", callback_data="set-currency-ils"),
        ],
        [
            InlineKeyboardButton(text="< Back", callback_data="settings"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await context.user_data["msg"].edit_text("Please, select a currency", reply_markup=reply_markup)


async def set_language_english_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["settings"]["language"] = "english"

    await settings_handler(update, context)


async def set_language_hebrew_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["settings"]["language"] = "hebrew"

    await settings_handler(update, context)


async def set_currency_ils_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["settings"]["currency"] = "ils"

    await settings_handler(update, context)


async def set_currency_usd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["settings"]["currency"] = "usd"

    await settings_handler(update, context)


async def display_wordlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if datetime.datetime.now() - context.user_data["last_login"] < datetime.timedelta(seconds=20):
        keyboard = [[InlineKeyboardButton(text="< Back", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        wordlist = "\n".join(context.user_data["wallet"].wordlist)
        await context.user_data["msg"].edit_text(
            f"<code>{wordlist}</code>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    else:
        # Login again before display
        await context.user_data["msg"].edit_text(LOGIN, parse_mode=ParseMode.HTML)
        context.user_data["redirect"] = "wordlist"
        return 'check-password'


async def refresh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Refreshing", show_alert=False)
    await context.user_data["wallet"].load_state()
    try:
        await show_wallet_options(update, context)
    except BadRequest:
        pass


handlers = {
    "new-password": new_password_handler,
    "check-password": check_password_handler,
    "confirm_password": confirm_password_handler,
    "send-address": send_address_handler,
    "send_amount": send_amount_handler,
    "send": send_handler,
    "receive": reactive_handler,
    "back": back_handler,
    "send-confirm": send_confirm_handler,
    "cancel-send": cancel_send_handler,
    "min_send": min_send_handler,
    "max_send": max_send_handler,
    "settings": settings_handler,
    "settings-language": change_language_handler,
    "settings-currency": change_currency_handler,
    "set-language-english": set_language_english_handler,
    "set-language-hebrew": set_language_hebrew_handler,
    "set-currency-usd": set_currency_usd_handler,
    "set-currency-ils": set_currency_ils_handler,
    "wordlist": display_wordlist_handler,
    "refresh": refresh_handler,
    "deeplink": deeplink_handler,
}

deeplink_handlers = {
    "transfer": send_transfer_handler,
    "accept": accept_transfer_handler
}

