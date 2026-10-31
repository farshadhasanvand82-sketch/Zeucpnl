import logging
import os
import time
import threading
from flask import Flask
from instagrapi import Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8963035503:AAFIAmyoKPqD70E4PYUjQVKz-lCKv40Ob_A"

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Instagram Automation Bot is Running Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

GET_USERNAME, GET_PASSWORD = range(2)

user_clients = {}      
user_rules = {}        
user_comment_rules = {}
user_temp_data = {}    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **به ربات هوشمند مدیریت اینستاگرام خوش آمدید.**\n\n"
        "برای شروع، لطفاً **نام کاربری (ایدی)** پیج اینستاگرام خود را ارسال کنید:"
    )
    return GET_USERNAME

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    username = update.message.text.strip()
    user_temp_data[chat_id] = username
    
    await update.message.reply_text(f"👤 آیدی ثبت شد: `{username}`\n\nاکنون لطفاً **رمز عبور (Password)** پیج را ارسال کنید:", parse_mode="Markdown")
    return GET_PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    password = update.message.text.strip()
    username = user_temp_data.get(chat_id)
    
    await update.message.reply_text("⏳ در حال اتصال به اینستاگرام، لطفاً چند لحظه صبر کنید...")
    
    cl = Client()
    
    try:
        cl.login(username, password)
        user_clients[chat_id] = cl
        user_rules[chat_id] = {}
        user_comment_rules[chat_id] = {}
        
        await update.message.reply_text("✅ **با موفقیت به اینستاگرام متصل شدید!** 🎉")
        await show_main_menu_from_message(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"خطا در لاگین: {e}")
        await update.message.reply_text(f"❌ خطا در لاگین: {e}\n\nلطفاً دوباره با دستور /start امتحان کنید.")
        return ConversationHandler.END

async def show_main_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📥 تنظیم پاسخ دایرکت", callback_data="menu_direct")],
        [InlineKeyboardButton("💬 تنظیم پاسخ کامنت", callback_data="menu_comment")],
        [InlineKeyboardButton("📋 مشاهده قوانین ثبت شده", callback_data="menu_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 **منوی اصلی مدیریت ربات:**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "menu_direct":
        await query.edit_message_text(
            "📥 **تنظیم پاسخ خودکار دایرکت**\n\n"
            "برای ثبت قانون جدید، از این فرمت در پیام بعدی استفاده کنید:\n"
            "`/setdirect کلمه_یا_عدد | متن_پاسخ`\n"
            "مثال: `/setdirect سلام | سلام وقتتون بخیر`",
            parse_mode="Markdown"
        )
    elif data == "menu_comment":
        await query.edit_message_text(
            "💬 **تنظیم پاسخ خودکار کامنت**\n\n"
            "برای ثبت قانون جدید کامنت، از این فرمت استفاده کنید:\n"
            "`/setcomment کلمه_یا_عدد | متن_پاسخ`\n"
            "مثال: `/setcomment قیمت | سلام، دایرکت چک شود.`",
            parse_mode="Markdown"
        )
    elif data == "menu_list":
        chat_id = query.message.chat_id
        d_rules = user_rules.get(chat_id, {})
        c_rules = user_comment_rules.get(chat_id, {})
        
        msg = "📋 **قوانین فعال شما:**\n\n**📥 دایرکت‌ها:**\n"
        for k, v in d_rules.items():
            msg += f"- `{k}` ➔ {v}\n"
        msg += "\n**💬 کامنت‌ها:**\n"
        for k, v in c_rules.items():
            msg += f"- `{k}` ➔ {v}\n"
            
        if not d_rules and not c_rules:
            msg = "📭 هیچ قانونی هنوز ثبت نشده است."
            
        await query.edit_message_text(msg, parse_mode="Markdown")

async def set_direct_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.replace("/setdirect", "").strip()
    if "|" not in text:
        await update.message.reply_text("⚠️ فرمت اشتباه! مثال:\n`/setdirect سلام | درود بر شما`", parse_mode="Markdown")
        return
    
    parts = text.split("|")
    kw = parts[0].strip().lower()
    res = parts[1].strip()
    
    if chat_id not in user_rules:
        user_rules[chat_id] = {}
    user_rules[chat_id][kw] = res
    
    await update.message.reply_text(f"✅ پاسخ خودکار دایرکت ثبت شد:\n🔑 `{kw}` ➔ 💬 `{res}`", parse_mode="Markdown")

async def set_comment_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.replace("/setcomment", "").strip()
    if "|" not in text:
        await update.message.reply_text("⚠️ فرمت اشتباه! مثال:\n`/setcomment قیمت | دایرکت چک شود`", parse_mode="Markdown")
        return
    
    parts = text.split("|")
    kw = parts[0].strip().lower()
    res = parts[1].strip()
    
    if chat_id not in user_comment_rules:
        user_comment_rules[chat_id] = {}
    user_comment_rules[chat_id][kw] = res
    
    await update.message.reply_text(f"✅ پاسخ خودکار کامنت ثبت شد:\n🔑 `{kw}` ➔ 💬 `{res}`", parse_mode="Markdown")

def background_monitor():
    while True:
        time.sleep(10)
        for chat_id, cl in list(user_clients.items()):
            try:
                threads = cl.direct_threads(amount=3)
                for thread in threads:
                    last_msg = thread.messages[0]
                    if last_msg.user_id != cl.user_id and last_msg.text:
                        txt = last_msg.text.strip().lower()
                        rules = user_rules.get(chat_id, {})
                        if txt in rules:
                            cl.direct_send(rules[txt], thread_ids=[thread.id])
                            logger.info(f"پاسخ دایرکت ارسال شد برای کلمه: {txt}")
                
                medias = cl.user_medias(cl.user_id, amount=2)
                for media in medias:
                    comments = cl.media_comments(media.pk, amount=5)
                    for comment in comments:
                        if comment.user.pk != cl.user_id and comment.text:
                            ctxt = comment.text.strip().lower()
                            c_rules = user_comment_rules.get(chat_id, {})
                            for kw, cres in c_rules.items():
                                if kw in ctxt:
                                    cl.media_comment_reply(media.pk, comment.pk, text=cres)
                                    logger.info(f"پاسخ کامنت ارسال شد برای کلمه: {kw}")
                                    break
            except Exception as e:
                logger.error(f"خطا در مانیتورینگ پس‌زمینه: {e}")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    instagram_thread = threading.Thread(target=background_monitor, daemon=True)
    instagram_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GET_USERNAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), receive_username)],
            GET_PASSWORD: [MessageHandler(filters.TEXT & (~filters.COMMAND), receive_password)],
        },
        fallbacks=[]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("setdirect", set_direct_rule))
    app.add_handler(CommandHandler("setcomment", set_comment_rule))
    
    print("ربات و وب‌سایت مانیتورینگ پورت فعال شدند...")
    app.run_polling(drop_pending_updates=True)
