import asyncio
import sys
import sqlite3 # مكتبة قاعدة البيانات المضافة

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.set_event_loop(asyncio.new_event_loop())

import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
# تأكد ان هذه الملفات موجودة عندك بنفس المجلد
from keyboards.city_keyboard import create_pick_city_keyboard
from keyboards.pick_person_keyboard import create_pick_person_keyboard
from helpers.format_all_iraq import format_all_iraq
from messages import msgs
from helpers.cities import city_gov_ids_arrays
from helpers.format_family_members import format_family_members
from utils import parse_person_callback_data, normalize_name
import db

load_dotenv()

# --- إعدادات المدير وقاعدة بيانات المشتركين ---
ADMIN_ID = 125827134  # الايدي مالتك

# دالة لإنشاء جدول المشتركين اذا ما كان موجود
def init_subscribers_db():
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

# دالة لإضافة مشترك جديد
def add_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# دالة لجلب كل المشتركين
def get_all_subscribers():
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# تشغيل قاعدة بيانات المشتركين اول ما يشتغل الملف
init_subscribers_db()
# ------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. حفظ المستخدم في قاعدة المشتركين
    add_subscriber(user.id)
    
    # 2. إرسال إشعار للمدير (أنت)
    try:
        if user.id != ADMIN_ID: # حتى ما يوصلك اشعار اذا انت دخلت
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 **شخص جديد دخل للبوت!**\n\n👤 الاسم: {user.first_name}\n🆔 الآيدي: `{user.id}`\n🔗 المعرف: @{user.username if user.username else 'لا يوجد'}",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"Error sending admin notification: {e}")

    # 3. رسالة الترحيب للمستخدم
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=msgs["start_message"], parse_mode="HTML"
    )

# --- دالة الإذاعة (إرسال للكل) ---
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التحقق ان المرسل هو المدير فقط
    if update.effective_user.id != ADMIN_ID:
        return

    # جلب النص بعد الأمر /send
    message_to_send = update.message.text.replace("/send", "").strip()
    
    if not message_to_send:
        await update.message.reply_text("⚠️ **خطأ:** اكتب الرسالة بعد الأمر.\nمثال: `/send مرحباً بالجميع`", parse_mode="Markdown")
        return

    users = get_all_subscribers()
    success_count = 0
    block_count = 0
    
    await update.message.reply_text(f"⏳ جاري الإرسال لـ {len(users)} مشترك...")

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_to_send)
            success_count += 1
        except Exception:
            # هذا يعني ان الشخص حاظر البوت
            block_count += 1
            
    await update.message.reply_text(
        f"✅ **تمت الإذاعة بنجاح!**\n\n📤 وصل لـ: {success_count}\n🚫 فشل (حظر): {block_count}",
        parse_mode="Markdown"
    )
# ----------------------------------

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=msgs["help_message"], parse_mode="HTML"
    )


async def three_part_name_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تم اضافة حفظ المستخدم هنا ايضاً للاحتياط
    add_subscriber(update.effective_user.id)
    
    context.user_data["first_name"] = normalize_name(update.message.text.split(" ")[0])
    context.user_data["middle_name"] = normalize_name(update.message.text.split(" ")[1])
    context.user_data["last_name"] = normalize_name(update.message.text.split(" ")[2])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""
        اختر المدينة التي تريد البحث فيها عن
الاسم الاول: {update.message.text.split(" ")[0]}
اسم الاب: {update.message.text.split(" ")[1]}
اسم الجد: {update.message.text.split(" ")[2]}
اذا كان الحقول خاطئة ، اضغط /help لتعلم الطريقة الصحيحة لادخال الاسم
        """,
        parse_mode="HTML",
        reply_markup=await create_pick_city_keyboard(),
    )


async def all_iraq_button_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = ""
    first_name = context.user_data.get("first_name", None)
    middle_name = context.user_data.get("middle_name", None)
    last_name = context.user_data.get("last_name", None)
    if first_name and middle_name and last_name:
        results = await db.find_all_iraq(first_name, middle_name, last_name)
        if len(results) == 0:
            message_text = msgs["no_person_found"]
        else:
            message_text = format_all_iraq(results)

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.callback_query.message.message_id,
            text=message_text,
            parse_mode="HTML",
        )
    else:
        await context.bot.answer_callback_query(
            callback_query_id=update.callback_query.id,
            text=msgs["button_outdated"],
            show_alert=True,
        )


async def city_button_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city_name"] = update.callback_query.data.split(":")[1]
    city_name = context.user_data.get("city_name", None)
    first_name = context.user_data.get("first_name", None)
    middle_name = context.user_data.get("middle_name", None)
    last_name = context.user_data.get("last_name", None)

    if first_name and middle_name and last_name and city_name:
        message_text = ""
        people = await db.find_in_city(
            first_name, middle_name, last_name, city_gov_ids_arrays[city_name]
        )
        if len(people) == 0:
            message_text = msgs["no_person_found"]
        else:
            message_text = msgs["please_pick_person_message"]
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=update.callback_query.message.message_id,
            text=message_text,
            parse_mode="HTML",
            reply_markup=await create_pick_person_keyboard(people),
        )
    else:
        await context.bot.answer_callback_query(
            callback_query_id=update.callback_query.id,
            text=msgs["button_outdated"],
            show_alert=True,
        )


async def person_button_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback_data_dict = parse_person_callback_data(update.callback_query.data)
    family_members = await db.find_family_members(
        callback_data_dict["fam"], callback_data_dict["gov"]
    )
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id,
        text=format_family_members(family_members),
        parse_mode="HTML",
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(os.environ.get("TOKEN")).build()

    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", help)
    # هاندلر الإذاعة الجديد
    broadcast_handler = CommandHandler("send", broadcast_message)
    
    three_part_name_search_handler = MessageHandler(
        filters.Regex(
            "^(?!.*[؟])([\u0600-\u06FF]+)\s+([\u0600-\u06FF]+)\s+([\u0600-\u06FF]+)"
        ),
        three_part_name_search,
    )
    all_iraq_button_clicked_handler = CallbackQueryHandler(
        all_iraq_button_clicked, pattern="city:all"
    )
    create_pick_person_keyboard_handler = CallbackQueryHandler(
        city_button_clicked, pattern="city:\w+"
    )
    person_button_clicked_handler = CallbackQueryHandler(
        person_button_clicked, pattern="\{fam:\d+,gov:\d+\}"
    )
    
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(broadcast_handler) # اضافة الهاندلر
    application.add_handler(three_part_name_search_handler)
    application.add_handler(all_iraq_button_clicked_handler)
    application.add_handler(create_pick_person_keyboard_handler)
    application.add_handler(person_button_clicked_handler)

    print("Bot is running...")
    application.run_polling()