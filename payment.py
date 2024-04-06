import os

from dotenv import load_dotenv
from telegram import LabeledPrice, Update, ShippingOption
from telegram.ext import ContextTypes

load_dotenv()

PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')


async def start_with_shipping_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends an invoice with shipping-payment."""
    chat_id = update.message.chat_id
    title = "Payment Example"
    description = "Payment Example using python-telegram-bot"
    # select a payload just for you to recognize its the donation from your bot
    payload = "Custom-Payload"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    currency = "USD"
    # price in dollars
    price = 1
    # price * 100 so as to include 2 decimal points
    # check https://core.telegram.org/bots/payments#supported-currencies for more details
    prices = [LabeledPrice("Test", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    await context.bot.send_invoice(
        chat_id,
        title,
        description,
        payload,
        PAYMENT_PROVIDER_TOKEN,
        currency,
        prices,
        need_name=True,
        need_phone_number=True,
        need_email=True,
        need_shipping_address=True,
        is_flexible=True,
    )


async def start_without_shipping_callback(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Sends an invoice without shipping-payment."""
    chat_id = update.message.chat_id
    title = "Payment Example"
    description = "Payment Example using python-telegram-bot"
    # select a payload just for you to recognize its the donation from your bot
    payload = "Custom-Payload"
    # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
    currency = "USD"
    # price in dollars
    price = 1
    # price * 100 so as to include 2 decimal points
    prices = [LabeledPrice("Test", price * 100)]

    # optionally pass need_name=True, need_phone_number=True,
    # need_email=True, need_shipping_address=True, is_flexible=True
    await context.bot.send_invoice(
        chat_id, title, description, payload, PAYMENT_PROVIDER_TOKEN, currency, prices
    )


async def shipping_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers the ShippingQuery with ShippingOptions"""
    query = update.shipping_query
    # check the payload, is this from your bot?
    if query.invoice_payload != "Custom-Payload":
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
        return

    # First option has a single LabeledPrice
    options = [ShippingOption("1", "Shipping Option A", [LabeledPrice("A", 100)])]
    # second option has an array of LabeledPrice objects
    price_list = [LabeledPrice("B1", 150), LabeledPrice("B2", 200)]
    options.append(ShippingOption("2", "Shipping Option B", price_list))
    await query.answer(ok=True, shipping_options=options)


# after (optional) shipping, it's the pre-checkout
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if query.invoice_payload != "Custom-Payload":
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)



