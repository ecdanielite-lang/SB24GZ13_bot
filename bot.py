import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Config (set these in Railway/Render Variables) ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/SB24GZ")           # your live channel
LATEST_LIVE_URL = os.getenv("LATEST_LIVE_URL", "https://t.me/SB24GZ")   # latest live link
CONTACT_URL = os.getenv("CONTACT_URL", "https://t.me/SB24GZ")           # contact/admin

# In-memory subscriber store (survives while bot runs)
SUBSCRIBERS = set()


# ---------- Helpers ----------
def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔴 Latest Live", callback_data="latest")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="notify")],
            [InlineKeyboardButton("ℹ️ About", callback_data="about")],
        ]
    )


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    text = (
        "👋 *Welcome to SB24GZ*\n"
        "_Receive updates when new live content is available._\n\n"
        "Choose an option below 👇"
    )
    kb = main_menu_keyboard()

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=kb, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use SB24GZ Bot*\n\n"
        "/start – Show main menu\n"
        "/latest – Get the latest live link\n"
        "/notify – Subscribe or unsubscribe from alerts\n"
        "/about – About this bot\n"
        "/help – This message",
        parse_mode="Markdown",
    )


async def latest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_latest(update, context)


async def notify_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_notify(update, context)


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_about(update, context)


# ---------- Button Actions ----------
async def send_latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔴 *Latest Live*\n\n"
        "Tap the button below to watch the current broadcast:"
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("▶️ Watch Live Now", url=LATEST_LIVE_URL)],
            [InlineKeyboardButton("📢 Open Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")],
        ]
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def send_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribed = user_id in SUBSCRIBERS

    status = "🔔 *Subscribed*" if subscribed else "🔕 *Not subscribed*"
    action_text = "Turn OFF notifications" if subscribed else "Turn ON notifications"
    action_data = "unsub" if subscribed else "sub"

    text = (
        f"🔔 *Notifications*\n\n"
        f"Status: {status}\n\n"
        "When enabled, you'll be alerted about new live broadcasts."
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(action_text, callback_data=action_data)],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")],
        ]
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def send_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *About SB24GZ*\n\n"
        "This bot sends updates and links for SB24GZ live broadcasts.\n\n"
        "• 100% free to use\n"
        "• No ads, no spam\n"
        "• Unsubscribe anytime via 🔔 Notifications\n\n"
        "📢 Channel: " + CHANNEL_URL + "\n"
        "📩 Contact: " + CONTACT_URL
    )
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Open Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")],
        ]
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


# ---------- Callback Router ----------
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await send_main_menu(update, context, edit=True)
    elif data == "latest":
        await send_latest(update, context)
    elif data == "notify":
        await send_notify(update, context)
    elif data == "about":
        await send_about(update, context)
    elif data == "sub":
        SUBSCRIBERS.add(update.effective_user.id)
        await send_notify(update, context)
    elif data == "unsub":
        SUBSCRIBERS.discard(update.effective_user.id)
        await send_notify(update, context)


# ---------- Fallback for plain text ----------
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please use the menu below 👇",
    )
    await send_main_menu(update, context)


# ---------- Broadcast (owner-only, optional) ----------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner can send: /broadcast Your message here
    Only works for OWNER_ID if set."""
    owner_id = os.getenv("OWNER_ID")
    if owner_id and str(update.effective_user.id) != str(owner_id):
        await update.message.reply_text("⛔ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast your message")
        return

    msg = " ".join(context.args)
    sent, failed = 0, 0
    for uid in list(SUBSCRIBERS):
        try:
            await context.bot.send_message(chat_id=uid, text=f"🔴 *Live Now!*\n\n{msg}", parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
            SUBSCRIBERS.discard(uid)
    await update.message.reply_text(f"✅ Sent: {sent}\n❌ Failed: {failed}")


# ---------- Main ----------
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN not set!")

    logger.info("Starting SB24GZ bot...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("latest", latest_cmd))
    app.add_handler(CommandHandler("notify", notify_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

    logger.info("🤖 SB24GZ bot is running.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
