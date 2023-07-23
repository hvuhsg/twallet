WELCOME_MESSAGE = "🆕 New Wallet\n\n" \
                  "<b>Welcome to the TON wallet bot!</b>\n\n" \
                  "To setup your wallet we will need you to choose a password\n" \
                  "Send the password as a text message"

LOGIN = "🔅 Login Required\n\n" \
        "<b>To protect your wallet we have logged you out</b>\n\n" \
        "Send your password as a text message"

RECEIPT = "✅ Transaction receipt: TON\n\n" \
          "<b>Address:</b> {address}\n" \
          "<b>Amount:</b> {amount} TON\n" \
          "<b>Fee:</b> {fee} TON\n\n" \
          "<b>Total:</b> {total} TON\n\n" \

WALLET_ADDRESS = "➕ Deposit: TON\n\n" \
                 "Use the address below to send TON to the Wallet bot address.\n" \
                 "Network: <b>The Open Network - TON.</b>\n\n" \
                 "<code>{address}</code>\n\n" \
                 "Funds will be credited within 2 minutes"

SEND_AMOUNT = "➡️ Transfer: TON\n\n" \
              "Indicate the amount you’d like to transfer via text message\n\n" \
              "<i>Min</i>: {min_amount} TON\n" \
              "<i>Max</i>: {max_amount} TON\n\n" \
              "<i>Fee</i>: ~{fee} TON"

SEND_ADDRESS = "➡️ Transfer: TON\n\n" \
               "Send the TON wallet address in text message here."

INVALID_ADDRESS = "🚫 Invalid Address\n\n" \
               "Send the TON wallet address in text message here."


SEND_CONFIRM = "➡️ Withdrawal confirmation: TON\n\n" \
               "<b>Address</b>: {address}\n\n" \
               "<b>Amount</b>: {amount} TON\n" \
               "<b>Fee</b>: {fee} TON\n" \
               "<b>Total amount</b>: {total_amount} TON\n" \
               "<b>Balance after</b>: {balance_after} TON\n\n" \
               "Do you confirm this operation?"

SETTINGS = "⚙️ Settings"
