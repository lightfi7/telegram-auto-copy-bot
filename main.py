import os
import payment
import logging
import pymongo
from typing import Optional, Tuple

from Crypto import Random
from Crypto.Cipher import AES
from dotenv import load_dotenv
from telegram import ChatMember, ChatMemberUpdated, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters, CallbackContext, CallbackQueryHandler, ShippingQueryHandler, PreCheckoutQueryHandler, )

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Replace 'SOURCE_CHANNEL_ID' with the ID of the channel you want to copy messages from
SOURCE_CHANNEL_ID = os.getenv('SOURCE_CHANNEL_ID')

print(BOT_TOKEN)

# config crypto
key = b'7f24a1b5c9d2f4e6'
iv = Random.new().read(AES.block_size)

# enable logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# constant
LANGUAGES = [['English', 'Spanish'], ['French', 'Korean']]

# db
client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["bear"]


def find_one(collection, query):
    return db[collection].find_one(query)


def find_many(collection, query):
    return db[collection].find(query)


def insert_one(collection, data):
    return db[collection].insert_one(data)


def insert_many(collection, data):
    return db[collection].insert_many(data)


def update_one(collection, query, data):
    return db[collection].update_one(query, {'$set': data})


def update_many(collection, query, data):
    return db[collection].update_many(query, data)


def delete_one(collection, query):
    return db[collection].delete_one(query)


def delete_many(collection, query):
    return db[collection].delete_many(query)


cache = {}


def cached(key, data):
    # local db
    if find_one('users', {'id': key}) is None:
        result = insert_one('users', data)
        print(result)

    # index db
    if key in cache:
        return cache[key]
    else:
        cache[key] = data
        return cache[key]


def is_hex(s):
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False


def generate_key(user):
    cipher = AES.new(key, AES.MODE_CFB, iv)
    user_data = f'{user.id}@{user.username}'
    return ''.join(f'{byte:02X}' for byte in cipher.encrypt(user_data.encode('utf-8')))


def verify_key(user, token):
    cipher = AES.new(key, AES.MODE_CFB, iv)
    decrypted_str = cipher.decrypt(token)
    return decrypted_str.decode('utf-8') == f'{user.id}@{user.username}'


async def start_command(update: Update, context: CallbackContext) -> None:
    user = cached(update.message.from_user.id,
                  {
                      'id': update.message.from_user.id,
                      'username': update.message.from_user.username,
                      'lang': 'English',
                  })

    msg = (
        "✨ Welcome!\n"
        "🌐 Please select your preferred language:"
    )

    keyboard = [[InlineKeyboardButton(lang, callback_data=f'@LANG_{lang}') for lang in langs] for langs in LANGUAGES]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, reply_markup=reply_markup)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    await query.answer()

    callback_type = query.data.split('_')[0]
    callback_data = query.data.split('_')[1]

    if callback_type == '@LANG':
        user = cached(query.from_user.id,
                      {
                          'id': query.from_user.id,
                          'username': query.from_user.username,
                          'lang': 'English',
                      })

        user['lang'] = callback_data
        user['perm'] = 'guest'

        update_one('users',
                   {'id': user['id']},
                   {
                       'lang': callback_data,
                       'perm': 'guest'
                   })

        await query.edit_message_text(text=f'🌐 Selected language: {callback_data}\n\n'
                                           f'🎁 Use the /membership command to upgrade your membership.')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'📌 @Support team\n`ry.mc.le.92@gmail.com`', parse_mode=ParseMode.MARKDOWN)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.channel_post is not None:
        logger.info("chat_id = %s", update.channel_post.chat.id)
        logger.info("text = %s", update.channel_post.text)
        if update.channel_post.chat.id == int(SOURCE_CHANNEL_ID):
            for user_id in cache.keys():
                if cache[user_id]['perm'] != 'guest':
                    await context.bot.copy_message(chat_id=user_id, from_chat_id=update.channel_post.chat.id,
                                                   message_id=update.channel_post.message_id)
    elif update.message is not None:
        user = cached(update.message.from_user.id,
                      {
                          'id': update.message.from_user.id,
                          'username': update.message.from_user.username,
                          'lang': 'English',
                          'level': 0
                      })
        if user['perm'] is None:
            await update.message.reply_text(text='😁 Start the bot using the /stat command.')
        elif user['perm'] != 'user':
            if is_hex(update.message.text) and verify_key(update.message.from_user, bytes.fromhex(update.message.text)):
                user['perm'] = 'user'
                update_one('users',
                           {'id': user['id']},
                           {
                               'perm': 'user',
                           })
                await update.message.reply_text(text='😍 Successfully started the bot')
            else:
                await update.message.reply_text(text='🤨 Invalid token. Please try again. If the problem persists, '
                                                     'please contact support.')
        else:
            await update.message.reply_text(text='😊')


# finally, after contacting the payment provider...
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirms the successful payment."""
    # do something after successfully receiving payment?
    user = cached(update.message.from_user.id, {
        'id': update.message.from_user.id,
        'username': update.message.from_user.username,
        'lang': 'English',
    })
    token = generate_key(update.message.from_user)
    user['token'] = token
    user['perm'] = 'guest'
    print(token)
    update_one('users',
               {'id': user['id']},
               {
                   'perm': 'guest',
                   'token': token
               })
    await update.message.reply_text(f"Thank you for your payment!\n")


def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Greets new users in chats and announces when someone leaves"""
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    cause_name = update.chat_member.from_user.mention_html()
    member_name = update.chat_member.new_chat_member.user.mention_html()

    if not was_member and is_member:
        await update.effective_chat.send_message(
            f"{member_name} was added by {cause_name}. Welcome!",
            parse_mode=ParseMode.HTML,
        )
    elif was_member and not is_member:
        await update.effective_chat.send_message(
            f"{member_name} is no longer with us. Thanks a lot, {cause_name} ...",
            parse_mode=ParseMode.HTML,
        )


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    # Add command handler to start the payment invoice
    application.add_handler(CommandHandler("membership", payment.start_with_shipping_callback))
    application.add_handler(CommandHandler("noshipping", payment.start_without_shipping_callback))

    # Optional handler if your product requires shipping
    application.add_handler(ShippingQueryHandler(payment.shipping_callback))

    # Pre-checkout handler to final check
    application.add_handler(PreCheckoutQueryHandler(payment.precheckout_callback))

    # Success! Notify your user!
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    application.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
