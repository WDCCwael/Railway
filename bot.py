import telebot
from telebot import types
import json
import datetime
import os
import time
import logging
import smtplib
import threading
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8369546185:AAEORmtlgrhIlRK7njn27DjjGO-v59IgQAw"
bot = telebot.TeleBot(TOKEN)

print("🚀 بدء تشغيل البوت الشامل المتكامل...")

# Configuration
DB_FILE = "professional_travel_bot.json"

# ✅ إعدادات البريد الإلكتروني المحدثة
EMAIL_CONFIG = {
    "smtp_server": "smtp.hostinger.com",
    "port": 465,
    "sender_email": "info@aht-s.com",
    "password": "Aa98989870$$",
    "admin_email": "a@aht-s.com"
}

# Database functions
def load_database():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading database: {e}")
    
    return {
        "bookings": [], 
        "users": {}, 
        "next_booking_id": 1, 
        "stats": {
            "total_bookings": 0, 
            "active_users": 0,
            "total_revenue": 0
        }
    }

def save_database(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving database: {e}")
        return False

def update_user_activity(user_id, username=None, first_name=None, language="ar"):
    db = load_database()
    user_id_str = str(user_id)
    
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "username": username,
            "first_name": first_name,
            "language": language,
            "join_date": datetime.datetime.now().isoformat(),
            "total_bookings": 0,
            "last_active": datetime.datetime.now().isoformat(),
            "bookings": []
        }
        db["stats"]["active_users"] = len(db["users"])
    else:
        db["users"][user_id_str]["last_active"] = datetime.datetime.now().isoformat()
        if username:
            db["users"][user_id_str]["username"] = username
        if first_name:
            db["users"][user_id_str]["first_name"] = first_name
    
    save_database(db)
    return db["users"][user_id_str]

def get_user_language(user_id):
    db = load_database()
    return db["users"].get(str(user_id), {}).get("language", "ar")

# وظائف التحقق من الصحة
def validate_phone(phone):
    """التحقق من صحة رقم الهاتف"""
    pattern = r'^\+?[\d\s\-\(\)]{10,}$'
    return re.match(pattern, phone) is not None

def validate_email(email):
    """التحقق من صحة البريد الإلكتروني"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_date(date_string):
    """التحقق من صحة التاريخ"""
    try:
        datetime.datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# نظام النسخ الاحتياطي
BACKUP_DIR = "backups"

def create_backup():
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            
        if os.path.exists(DB_FILE):
            backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            import shutil
            shutil.copy2(DB_FILE, backup_file)
            
            # حذف النسخ القديمة (الاحتفاظ بـ 10 نسخ فقط)
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')])
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    os.remove(os.path.join(BACKUP_DIR, old_backup))
                    
            logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_file}")
    except Exception as e:
        logger.error(f"❌ فشل في إنشاء نسخة احتياطية: {e}")

# ✅ خدمة البريد الإلكتروني المحدثة مع الإعدادات الصحيحة
def send_booking_email(user_data, booking_id, lang="ar"):
    """إرسال تأكيد الحجز عبر البريد الإلكتروني مع الإعدادات المحدثة"""
    try:
        # تحديد موضوع البريد حسب اللغة
        if lang == "ar":
            subject = f"تأكيد حجز جديد #{booking_id} - AHT Travel"
        elif lang == "ru":
            subject = f"Подтверждение нового бронирования #{booking_id} - AHT Travel"
        else:
            subject = f"New Booking Confirmation #{booking_id} - AHT Travel"
        
        # محتوى البريد الإلكتروني
        if lang == "ar":
            body = f"""
🎉 تم استلام حجز جديد من نظام البوت

📋 تفاصيل الحجز:
====================
🔸 رقم الحجز: #{booking_id}
👤 الاسم: {user_data.get('name', 'غير محدد')}
📞 الهاتف: {user_data.get('phone', 'غير محدد')}
📧 البريد الإلكتروني: {user_data.get('email', 'غير محدد')}
🎯 نوع الرحلة: {user_data.get('tour_name', 'غير محدد')}
💰 السعر: ${user_data.get('price', 0)}
👥 عدد الأشخاص: {user_data.get('people', 1)}
📅 تاريخ الحجز: {user_data.get('booking_date', 'غير محدد')}
🏨 الفندق: {user_data.get('hotel', 'غير محدد')}
🌍 الجنسية: {user_data.get('nationality', 'غير محدد')}
💵 السعر الإجمالي: ${user_data.get('price', 0) * user_data.get('people', 1)}

⏰ وقت الاستلام: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
====================

📞 للتواصل: {PROFESSIONAL_DATA['company']['phone']}
✨ AHT Travel - خدمة العملاء
"""
        elif lang == "ru":
            body = f"""
🎉 Новое бронирование из бота

📋 Детали бронирования:
====================
🔸 Номер брони: #{booking_id}
👤 Имя: {user_data.get('name', 'Не указано')}
📞 Телефон: {user_data.get('phone', 'Не указано')}
📧 Email: {user_data.get('email', 'Не указано')}
🎯 Тур: {user_data.get('tour_name', 'Не указано')}
💰 Цена: ${user_data.get('price', 0)}
👥 Количество людей: {user_data.get('people', 1)}
📅 Дата брони: {user_data.get('booking_date', 'Не указано')}
🏨 Отель: {user_data.get('hotel', 'Не указано')}
🌍 Национальность: {user_data.get('nationality', 'Не указано')}
💵 Общая цена: ${user_data.get('price', 0) * user_data.get('people', 1)}

⏰ Получено: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
====================

📞 Для связи: {PROFESSIONAL_DATA['company']['phone']}
✨ AHT Travel - Обслуживание клиентов
"""
        else:
            body = f"""
🎉 New Booking from Bot System

📋 Booking Details:
====================
🔸 Booking ID: #{booking_id}
👤 Name: {user_data.get('name', 'Not specified')}
📞 Phone: {user_data.get('phone', 'Not specified')}
📧 Email: {user_data.get('email', 'Not specified')}
🎯 Tour: {user_data.get('tour_name', 'Not specified')}
💰 Price: ${user_data.get('price', 0)}
👥 People: {user_data.get('people', 1)}
📅 Booking Date: {user_data.get('booking_date', 'Not specified')}
🏨 Hotel: {user_data.get('hotel', 'Not specified')}
🌍 Nationality: {user_data.get('nationality', 'Not specified')}
💵 Total Price: ${user_data.get('price', 0) * user_data.get('people', 1)}

⏰ Received at: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
====================

📞 Contact: {PROFESSIONAL_DATA['company']['phone']}
✨ AHT Travel - Customer Service
"""

        # إنشاء رسالة البريد
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["sender_email"]
        msg['To'] = EMAIL_CONFIG["admin_email"]
        msg['Subject'] = subject
        
        # إضافة محتوى البريد
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # ✅ الاتصال باستخدام SSL
        context = smtplib.ssl.create_default_context()
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"], context=context) as server:
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["password"])
            server.send_message(msg)
        
        logger.info(f"✅ تم إرسال البريد الإلكتروني بنجاح للحجز #{booking_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل في إرسال البريد الإلكتروني: {e}")
        return False

# ✅ اختبار اتصال البريد الإلكتروني
def test_email_connection():
    """اختبار اتصال البريد الإلكتروني"""
    try:
        context = smtplib.ssl.create_default_context()
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"], context=context) as server:
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["password"])
        print("✅ اتصال البريد الإلكتروني ناجح")
        return True
    except Exception as e:
        print(f"❌ فشل اتصال البريد الإلكتروني: {e}")
        return False

# البيانات المهنية الشاملة
PROFESSIONAL_DATA = {
    "company": {
        "name_ar": "AHT Travel",
        "name_ru": "AHT Travel", 
        "name_en": "AHT Travel",
        "phone": "+201030319293",
        "email": "info@aht-s.com",
        "website": "https://aht-s.com",
        "address_ar": "الغردقة، مصر",
        "address_ru": "Хургада, Египет",
        "address_en": "Hurghada, Egypt"
    },
    "categories": {
        "premium_tours": {
            "name_ar": "⭐ الجولات المميزة",
            "name_ru": "⭐ Премиум туры",
            "name_en": "⭐ Premium Tours",
            "icon": "⭐",
            "tours": [
                {
                    "id": 1,
                    "name_ar": "رحلة القاهرة الفاخرة",
                    "name_ru": "Роскошный тур в Каир", 
                    "name_en": "Luxury Cairo Tour",
                    "price": 150,
                    "duration_ar": "يومان",
                    "duration_ru": "2 дня",
                    "duration_en": "2 days",
                    "description_ar": "جولة شاملة مع فندق 5 نجوم ومرشد خاص",
                    "description_ru": "Все включено с отелем 5 звезд и личным гидом",
                    "description_en": "All inclusive with 5-star hotel and private guide",
                    "highlights_ar": ["فندق فاخر", "مرشد خاص", "عشاء في النيل", "تذاكر مجانية"],
                    "highlights_ru": ["Роскошный отель", "Личный гид", "Ужин на Ниле", "Бесплатные билеты"],
                    "highlights_en": ["Luxury hotel", "Private guide", "Nile dinner", "Free tickets"],
                    "image": "https://via.placeholder.com/400x200/4A90E2/FFFFFF?text=Luxury+Cairo+Tour"
                }
            ]
        }
    },
    "services": {
        "included_ar": ["النقل من الفندق", "مرشد سياحي", "تذاكر الدخول", "تأمين صحي", "وجبات", "مشروبات"],
        "included_ru": ["Трансфер из отеля", "Гид", "Входные билеты", "Медицинская страховка", "Питание", "Напитки"],
        "included_en": ["Hotel transfer", "Tour guide", "Entrance tickets", "Health insurance", "Meals", "Drinks"],
        "languages_ar": ["العربية", "الإنجليزية", "الروسية", "الألمانية", "الفرنسية"],
        "languages_ru": ["Арабский", "Английский", "Русский", "Немецкий", "Французский"],
        "languages_en": ["Arabic", "English", "Russian", "German", "French"]
    }
}

# جلسات المستخدمين
user_sessions = {}

# ✅ اختبار الاتصال عند بدء التشغيل
print("🔍 اختبار اتصال البريد الإلكتروني...")
test_email_connection()

# المعالجات الرئيسية
@bot.message_handler(commands=['start', 'menu', 'help'])
def start_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    update_user_activity(
        user_id, 
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    show_language_selection(chat_id)

def show_language_selection(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    
    welcome_text = """
🏝️ *AHT Travel - نظام الحجوزات الاحترافي*

🌍 *AHT Travel - Professional Booking System*  

🌍 *AHT Travel - Профессиональная система бронирования*

الرجاء اختيار اللغة / Please choose your language / Пожалуйста, выберите язык:
"""
    
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    language = call.data.replace('lang_', '')
    
    user_data = update_user_activity(user_id, language=language)
    user_sessions[user_id] = {"language": language, "step": "main_menu"}
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    show_main_dashboard(chat_id, language)

def show_main_dashboard(chat_id, lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == "ar":
        buttons = [
            '⭐ جولات مميزة', '🏛️ رحلات تاريخية', '🎯 مغامرات',
            '📊 إحصائيات', '💰 عروض خاصة', '🏆 خدماتنا',
            '📞 اتصل بنا', '🔄 تغيير اللغة',
            '📋 حجوزاتي', '🎁 عروض حصرية'
        ]
        welcome_text = f"""
🏝️ *{PROFESSIONAL_DATA["company"]["name_ar"]} - النظام الشامل*

مرحباً بك في نظام الحجوزات المتقدم! 🌟

*اختر من القائمة:*
"""
    elif lang == "ru":
        buttons = [
            '⭐ Премиум туры', '🏛️ Исторические', '🎯 Приключения', 
            '📊 Статистика', '💰 Акции', '🏆 Услуги',
            '📞 Контакты', '🔄 Сменить язык',
            '📋 Мои брони', '🎁 Эксклюзивные предложения'
        ]
        welcome_text = f"""
🏝️ *{PROFESSIONAL_DATA["company"]["name_ru"]} - Комплексная система*

Добро пожаловать в продвинутую систему бронирования! 🌟

*Выберите из меню:*
"""
    else:
        buttons = [
            '⭐ Premium Tours', '🏛️ Historical', '🎯 Adventures',
            '📊 Statistics', '💰 Special Offers', '🏆 Our Services', 
            '📞 Contact Us', '🔄 Change Language',
            '📋 My Bookings', '🎁 Exclusive Offers'
        ]
        welcome_text = f"""
🏝️ *{PROFESSIONAL_DATA["company"]["name_en"]} - Complete System*

Welcome to the advanced booking system! 🌟

*Choose from menu:*
"""
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(types.KeyboardButton(buttons[i]), types.KeyboardButton(buttons[i+1]))
        else:
            markup.add(types.KeyboardButton(buttons[i]))
    
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_main_menu(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text
    
    lang = get_user_language(user_id)
    update_user_activity(user_id)
    
    if '⭐' in text:
        show_tours_by_category(chat_id, "premium_tours", lang)
    elif '🏛️' in text:
        show_tours_by_category(chat_id, "historical", lang)
    elif '🎯' in text:
        show_tours_by_category(chat_id, "adventure", lang)
    elif '📊' in text:
        show_statistics(chat_id, user_id, lang)
    elif '💰' in text:
        show_special_offers(chat_id, lang)
    elif '🏆' in text:
        show_our_services(chat_id, lang)
    elif '📞' in text:
        show_contact_info(chat_id, lang)
    elif '🔄' in text:
        show_language_selection(chat_id)
    elif '📋' in text:
        show_user_bookings(chat_id, user_id, lang)
    elif '🎁' in text:
        show_exclusive_offers(chat_id, lang)
    else:
        send_quick_reply(chat_id, lang)

def show_tours_by_category(chat_id, category_key, lang):
    category = PROFESSIONAL_DATA["categories"][category_key]
    
    for tour in category["tours"]:
        send_tour_card(chat_id, tour, category, lang)

def send_tour_card(chat_id, tour, category, lang):
    if lang == "ar":
        text = f"""
{category['icon']} *{tour['name_ar']}*

💰 *السعر:* ${tour['price']} / شخص
⏱️ *المدة:* {tour['duration_ar']}
📝 *الوصف:* {tour['description_ar']}

⭐ *المميزات:*
"""
        for highlight in tour["highlights_ar"]:
            text += f"• {highlight}\n"
    elif lang == "ru":
        text = f"""
{category['icon']} *{tour['name_ru']}*

💰 *Цена:* ${tour['price']} / человек
⏱️ *Продолжительность:* {tour['duration_ru']}
📝 *Описание:* {tour['description_ru']}

⭐ *Особенности:*
"""
        for highlight in tour["highlights_ru"]:
            text += f"• {highlight}\n"
    else:
        text = f"""
{category['icon']} *{tour['name_en']}*

💰 *Price:* ${tour['price']} / person
⏱️ *Duration:* {tour['duration_en']}
📝 *Description:* {tour['description_en']}

⭐ *Highlights:*
"""
        for highlight in tour["highlights_en"]:
            text += f"• {highlight}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if lang == "ar":
        markup.add(
            types.InlineKeyboardButton("🎯 احجز الآن", callback_data=f"book_{tour['id']}"),
            types.InlineKeyboardButton("💬 استفسار", callback_data=f"inquiry_{tour['id']}")
        )
    elif lang == "ru":
        markup.add(
            types.InlineKeyboardButton("🎯 Забронировать", callback_data=f"book_{tour['id']}"),
            types.InlineKeyboardButton("💬 Узнать", callback_data=f"inquiry_{tour['id']}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("🎯 Book Now", callback_data=f"book_{tour['id']}"),
            types.InlineKeyboardButton("💬 Inquiry", callback_data=f"inquiry_{tour['id']}")
        )
    
    try:
        bot.send_photo(
            chat_id, 
            tour.get('image', 'https://via.placeholder.com/400x200/4A90E2/FFFFFF?text=AHT+Travel'),
            caption=text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

# ✅ عملية الحجز المحدثة مع البريد الإلكتروني
@bot.callback_query_handler(func=lambda call: call.data.startswith('book_'))
def start_booking_process(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    tour_id = int(call.data.replace('book_', ''))
    
    lang = get_user_language(user_id)
    
    # البحث عن الرحلة
    tour = None
    for category in PROFESSIONAL_DATA["categories"].values():
        for t in category["tours"]:
            if t["id"] == tour_id:
                tour = t
                break
        if tour:
            break
    
    if not tour:
        error_msg = "Tour not found" if lang == "en" else "Тур не найден" if lang == "ru" else "الرحلة غير موجودة"
        bot.answer_callback_query(call.id, error_msg)
        return
    
    # بدء جلسة الحجز للمستخدم
    user_sessions[user_id] = {
        "language": lang,
        "step": "get_name",
        "booking_data": {
            "tour_id": tour_id,
            "tour_name": tour[f"name_{lang}"],
            "price": tour["price"]
        }
    }
    
    if lang == "ar":
        text = f"""
🎯 *بدء عملية الحجز*

*الرحلة:* {tour['name_ar']}
*السعر:* ${tour['price']} / شخص

📝 *الرجاء إدخال البيانات التالية:*

👉 *الاسم الكامل:*
"""
    elif lang == "ru":
        text = f"""
🎯 *Начало бронирования*

*Тур:* {tour['name_ru']}
*Цена:* ${tour['price']} / человек

📝 *Пожалуйста, введите следующие данные:*

👉 *Полное имя:*
"""
    else:
        text = f"""
🎯 *Starting Booking Process*

*Tour:* {tour['name_en']}
*Price:* ${tour['price']} / person

📝 *Please enter the following details:*

👉 *Full Name:*
"""
    
    bot.send_message(chat_id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# معالجات خطوات الحجز - مصححة
@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_name')
def get_name(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    user_sessions[user_id]["booking_data"]["name"] = message.text
    user_sessions[user_id]["step"] = "get_phone"
    
    prompt = "📞 *رقم الهاتف:*" if lang == "ar" else "📞 *Номер телефона:*" if lang == "ru" else "📞 *Phone Number:*"
    bot.send_message(chat_id, prompt, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_phone')
def get_phone(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    # ✅ التحقق من صحة الهاتف
    if not validate_phone(message.text):
        error_msg = "⚠️ يرجى إدخال رقم هاتف صحيح" if lang == "ar" else "⚠️ Пожалуйста, введите правильный номер телефона" if lang == "ru" else "⚠️ Please enter a valid phone number"
        bot.send_message(chat_id, error_msg)
        return
    
    user_sessions[user_id]["booking_data"]["phone"] = message.text
    user_sessions[user_id]["step"] = "get_email"
    
    prompt = "📧 *البريد الإلكتروني:*" if lang == "ar" else "📧 *Электронная почта:*" if lang == "ru" else "📧 *Email:*"
    bot.send_message(chat_id, prompt, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_email')
def get_email(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    # ✅ التحقق من صحة البريد الإلكتروني
    if not validate_email(message.text):
        error_msg = "⚠️ يرجى إدخال بريد إلكتروني صحيح" if lang == "ar" else "⚠️ Пожалуйста, введите правильный email" if lang == "ru" else "⚠️ Please enter a valid email"
        bot.send_message(chat_id, error_msg)
        return
    
    user_sessions[user_id]["booking_data"]["email"] = message.text
    user_sessions[user_id]["step"] = "get_people"
    
    prompt = "👥 *عدد الأشخاص:*" if lang == "ar" else "👥 *Количество людей:*" if lang == "ru" else "👥 *Number of People:*"
    bot.send_message(chat_id, prompt, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_people')
def get_people(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    try:
        people = int(message.text)
        if people <= 0:
            raise ValueError("يجب أن يكون العدد أكبر من الصفر")
        user_sessions[user_id]["booking_data"]["people"] = people
        user_sessions[user_id]["step"] = "get_date"
        
        prompt = "📅 *تاريخ الحجز (YYYY-MM-DD):*" if lang == "ar" else "📅 *Дата брони (YYYY-MM-DD):*" if lang == "ru" else "📅 *Booking Date (YYYY-MM-DD):*"
        bot.send_message(chat_id, prompt, parse_mode='Markdown')
    except:
        error_msg = "⚠️ يرجى إدخال رقم صحيح أكبر من الصفر" if lang == "ar" else "⚠️ Пожалуйста, введите целое число больше нуля" if lang == "ru" else "⚠️ Please enter a valid number greater than zero"
        bot.send_message(chat_id, error_msg)

@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_date')
def get_date(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    # ✅ التحقق من صحة التاريخ
    if not validate_date(message.text):
        error_msg = "⚠️ يرجى إدخال تاريخ صحيح (YYYY-MM-DD)" if lang == "ar" else "⚠️ Пожалуйста, введите правильную дату (YYYY-MM-DD)" if lang == "ru" else "⚠️ Please enter a valid date (YYYY-MM-DD)"
        bot.send_message(chat_id, error_msg)
        return
    
    user_sessions[user_id]["booking_data"]["booking_date"] = message.text
    user_sessions[user_id]["step"] = "get_hotel"
    
    prompt = "🏨 *اسم الفندق:*" if lang == "ar" else "🏨 *Название отеля:*" if lang == "ru" else "🏨 *Hotel Name:*"
    bot.send_message(chat_id, prompt, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_hotel')
def get_hotel(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    user_sessions[user_id]["booking_data"]["hotel"] = message.text
    user_sessions[user_id]["step"] = "get_nationality"
    
    prompt = "🌍 *الجنسية:*" if lang == "ar" else "🌍 *Национальность:*" if lang == "ru" else "🌍 *Nationality:*"
    bot.send_message(chat_id, prompt, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_sessions.get(message.from_user.id, {}).get('step') == 'get_nationality')
def get_nationality(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    lang = user_sessions[user_id]["language"]
    
    user_sessions[user_id]["booking_data"]["nationality"] = message.text
    user_sessions[user_id]["step"] = "confirm_booking"
    
    show_booking_confirmation(chat_id, user_id, lang)

def show_booking_confirmation(chat_id, user_id, lang):
    booking_data = user_sessions[user_id]["booking_data"]
    total_price = booking_data['price'] * booking_data['people']
    
    if lang == "ar":
        text = f"""
✅ *تفاصيل الحجز*

*الرحلة:* {booking_data['tour_name']}
*الاسم:* {booking_data['name']}
*الهاتف:* {booking_data['phone']}
*البريد:* {booking_data['email']}
*عدد الأشخاص:* {booking_data['people']}
*التاريخ:* {booking_data['booking_date']}
*الفندق:* {booking_data['hotel']}
*الجنسية:* {booking_data['nationality']}
*السعر الإجمالي:* ${total_price}

📧 *سيتم إرسال تأكيد بالبريد الإلكتروني*

هل تريد تأكيد الحجز؟
"""
    elif lang == "ru":
        text = f"""
✅ *Детали бронирования*

*Тур:* {booking_data['tour_name']}
*Имя:* {booking_data['name']}
*Телефон:* {booking_data['phone']}
*Email:* {booking_data['email']}
*Количество людей:* {booking_data['people']}
*Дата:* {booking_data['booking_date']}
*Отель:* {booking_data['hotel']}
*Национальность:* {booking_data['nationality']}
*Общая цена:* ${total_price}

📧 *Подтверждение будет отправлено по электронной почте*

Подтвердить бронирование?
"""
    else:
        text = f"""
✅ *Booking Details*

*Tour:* {booking_data['tour_name']}
*Name:* {booking_data['name']}
*Phone:* {booking_data['phone']}
*Email:* {booking_data['email']}
*People:* {booking_data['people']}
*Date:* {booking_data['booking_date']}
*Hotel:* {booking_data['hotel']}
*Nationality:* {booking_data['nationality']}
*Total Price:* ${total_price}

📧 *Confirmation will be sent by email*

Confirm booking?
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    if lang == "ar":
        markup.add(
            types.InlineKeyboardButton("✅ تأكيد الحجز", callback_data="confirm_booking"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_booking")
        )
    elif lang == "ru":
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("✅ Confirm Booking", callback_data="confirm_booking"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_booking")
        )
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in ['confirm_booking', 'cancel_booking'])
def handle_booking_confirmation(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    if user_id not in user_sessions:
        bot.answer_callback_query(call.id, "Session expired")
        return
    
    lang = user_sessions[user_id]["language"]
    booking_data = user_sessions[user_id]["booking_data"]
    
    if call.data == 'confirm_booking':
        # حفظ الحجز في قاعدة البيانات
        db = load_database()
        booking_id = db["next_booking_id"]
        total_price = booking_data['price'] * booking_data['people']
        
        booking_record = {
            "id": booking_id,
            "user_id": user_id,
            "user_name": booking_data['name'],
            "user_phone": booking_data['phone'],
            "user_email": booking_data['email'],
            "tour_id": booking_data['tour_id'],
            "tour_name": booking_data['tour_name'],
            "people": booking_data['people'],
            "total_price": total_price,
            "booking_date": booking_data['booking_date'],
            "hotel": booking_data['hotel'],
            "nationality": booking_data['nationality'],
            "status": "confirmed",
            "created_at": datetime.datetime.now().isoformat(),
            "language": lang
        }
        
        db["bookings"].append(booking_record)
        db["next_booking_id"] += 1
        db["stats"]["total_bookings"] += 1
        db["stats"]["total_revenue"] += total_price
        
        # تحديث إحصائيات المستخدم
        user_id_str = str(user_id)
        if user_id_str in db["users"]:
            db["users"][user_id_str]["total_bookings"] = db["users"][user_id_str].get("total_bookings", 0) + 1
            if "bookings" not in db["users"][user_id_str]:
                db["users"][user_id_str]["bookings"] = []
            db["users"][user_id_str]["bookings"].append(booking_id)
        
        save_database(db)
        
        # ✅ إرسال إشعار البريد الإلكتروني
        email_thread = threading.Thread(
            target=send_booking_email, 
            args=(booking_data, booking_id, lang)
        )
        email_thread.start()
        
        if lang == "ar":
            success_text = f"""
🎉 *تم تأكيد الحجز بنجاح!*

*رقم الحجز:* #{booking_id}
*سيتم التواصل معك خلال 24 ساعة*

📧 *تم إرسال تأكيد بالبريد الإلكتروني*

📞 للاستفسار: {PROFESSIONAL_DATA['company']['phone']}
"""
        elif lang == "ru":
            success_text = f"""
🎉 *Бронирование подтверждено!*

*Номер брони:* #{booking_id}
*С вами свяжутся в течение 24 часов*

📧 *Подтверждение отправлено по электронной почте*

📞 Для вопросов: {PROFESSIONAL_DATA['company']['phone']}
"""
        else:
            success_text = f"""
🎉 *Booking Confirmed!*

*Booking ID:* #{booking_id}
*We will contact you within 24 hours*

📧 *Confirmation sent by email*

📞 For inquiries: {PROFESSIONAL_DATA['company']['phone']}
"""
        
        bot.edit_message_text(
            success_text,
            chat_id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        # مسح جلسة المستخدم
        if user_id in user_sessions:
            del user_sessions[user_id]
            
    else:  # إلغاء الحجز
        if lang == "ar":
            cancel_text = "❌ تم إلغاء الحجز"
        elif lang == "ru":
            cancel_text = "❌ Бронирование отменено"
        else:
            cancel_text = "❌ Booking cancelled"
        
        bot.edit_message_text(
            cancel_text,
            chat_id,
            call.message.message_id
        )
        
        if user_id in user_sessions:
            del user_sessions[user_id]
    
    bot.answer_callback_query(call.id)

# الميزات الإضافية
def show_user_bookings(chat_id, user_id, lang):
    db = load_database()
    user_bookings = []
    
    for booking in db["bookings"]:
        if booking.get("user_id") == user_id:
            user_bookings.append(booking)
    
    if not user_bookings:
        if lang == "ar":
            text = "📭 لا توجد حجوزات سابقة"
        elif lang == "ru":
            text = "📭 Нет предыдущих бронирований"
        else:
            text = "📭 No previous bookings"
        
        bot.send_message(chat_id, text)
        return
    
    if lang == "ar":
        text = "📋 *حجوزاتي السابقة*\n\n"
    elif lang == "ru":
        text = "📋 *Мои предыдущие бронирования*\n\n"
    else:
        text = "📋 *My Previous Bookings*\n\n"
    
    for booking in user_bookings[:5]:
        text += f"🔸 #{booking['id']} - {booking['tour_name']}\n"
        text += f"   👥 {booking['people']} أشخاص | 💰 ${booking['total_price']}\n"
        text += f"   📅 {booking['booking_date']} | 🏨 {booking['hotel']}\n\n"
    
    bot.send_message(chat_id, text, parse_mode='Markdown')

def show_exclusive_offers(chat_id, lang):
    if lang == "ar":
        text = f"""
🎁 *عروض حصرية*

✨ *خصم 30% للحجز المبكر*
- احجز قبل 7 أيام واحصل على خصم 30%

✨ *عرض العائلة المميز*
- طفلين مجاناً مع كل حجز عائلي

✨ *ترقية مجانية*
- ترقية إلى فندق 5 نجوم مجاناً

📞 للاستفادة من العروض: {PROFESSIONAL_DATA['company']['phone']}
"""
    elif lang == "ru":
        text = f"""
🎁 *Эксклюзивные предложения*

✨ *Скидка 30% при раннем бронировании*
- Забронируйте за 7 дней и получите скидку 30%

✨ *Специальное семейное предложение*
- 2 ребенка бесплатно с каждым семейным бронированием

✨ *Бесплатное улучшение*
- Бесплатное улучшение до отеля 5 звезд

📞 Чтобы воспользоваться предложениями: {PROFESSIONAL_DATA['company']['phone']}
"""
    else:
        text = f"""
🎁 *Exclusive Offers*

✨ *30% Early Booking Discount*
- Book 7 days in advance and get 30% discount

✨ *Special Family Offer*
- 2 children free with every family booking

✨ *Free Upgrade*
- Free upgrade to 5-star hotel

📞 To benefit from offers: {PROFESSIONAL_DATA['company']['phone']}
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "📞 اتصل الآن" if lang == "ar" else "📞 Позвонить" if lang == "ru" else "📞 Call Now",
        url=f"tel:{PROFESSIONAL_DATA['company']['phone']}"
    ))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

def show_statistics(chat_id, user_id, lang):
    db = load_database()
    stats = db["stats"]
    user = db["users"].get(str(user_id), {})
    
    if lang == "ar":
        text = f"""
📊 *الإحصائيات الشاملة*

👥 *إجمالي العملاء:* {stats['active_users']}
🗓️ *إجمالي الحجوزات:* {stats['total_bookings']}
💰 *إجمالي الإيرادات:* ${stats['total_revenue']}
🌟 *حجوزاتك:* {user.get('total_bookings', 0)}
📅 *انضممت في:* {user.get('join_date', '')[:10]}
"""
    elif lang == "ru":
        text = f"""
📊 *Комплексная статистика*

👥 *Всего клиентов:* {stats['active_users']}
🗓️ *Всего бронирований:* {stats['total_bookings']}
💰 *Общий доход:* ${stats['total_revenue']}
🌟 *Ваши брони:* {user.get('total_bookings', 0)}
📅 *Вы присоединились:* {user.get('join_date', '')[:10]}
"""
    else:
        text = f"""
📊 *Comprehensive Statistics*

👥 *Total Clients:* {stats['active_users']}
🗓️ *Total Bookings:* {stats['total_bookings']}
💰 *Total Revenue:* ${stats['total_revenue']}
🌟 *Your Bookings:* {user.get('total_bookings', 0)}
📅 *Joined:* {user.get('join_date', '')[:10]}
"""
    
    bot.send_message(chat_id, text, parse_mode='Markdown')

def show_our_services(chat_id, lang):
    services = PROFESSIONAL_DATA["services"]
    
    if lang == "ar":
        text = """
🏆 *خدماتنا الشاملة*

✅ *الخدمات المشمولة:*
"""
        for service in services["included_ar"]:
            text += f"• {service}\n"
        
        text += "\n🌍 *اللغات المتاحة:*\n"
        for language in services["languages_ar"]:
            text += f"• {language}\n"
            
    elif lang == "ru":
        text = """
🏆 *Наши комплексные услуги*

✅ *Включенные услуги:*
"""
        for service in services["included_ru"]:
            text += f"• {service}\n"
        
        text += "\n🌍 *Доступные языки:*\n"
        for language in services["languages_ru"]:
            text += f"• {language}\n"
    else:
        text = """
🏆 *Our Comprehensive Services*

✅ *Included Services:*
"""
        for service in services["included_en"]:
            text += f"• {service}\n"
        
        text += "\n🌍 *Available Languages:*\n"
        for language in services["languages_en"]:
            text += f"• {language}\n"
    
    bot.send_message(chat_id, text, parse_mode='Markdown')

def show_contact_info(chat_id, lang):
    company = PROFESSIONAL_DATA["company"]
    
    if lang == "ar":
        text = f"""
📞 *معلومات الاتصال الشاملة*

🏢 *الشركة:* {company['name_ar']}
📞 *هاتف الحجز:* {company['phone']}
📧 *البريد الإلكتروني:* {company['email']}
🌐 *الموقع الإلكتروني:* {company['website']}
📍 *العناص:* {company['address_ar']}

🕒 *ساعات العمل:* 24/7
💼 *مدير الحساب:* أحمد جابر

✨ *نحن هنا لخدمتك على مدار الساعة!*
"""
    elif lang == "ru":
        text = f"""
📞 *Комплексная контактная информация*

🏢 *Компания:* {company['name_ru']}
📞 *Телефон бронирования:* {company['phone']}
📧 *Электронная почта:* {company['email']}
🌐 *Веб-сайт:* {company['website']}
📍 *Адрес:* {company['address_ru']}

🕒 *Часы работы:* 24/7
💼 *Аккаунт менеджер:* Ахмед Габер

✨ *Мы здесь для вас 24/7!*
"""
    else:
        text = f"""
📞 *Comprehensive Contact Information*

🏢 *Company:* {company['name_en']}
📞 *Booking Phone:* {company['phone']}
📧 *Email:* {company['email']}
🌐 *Website:* {company['website']}
📍 *Address:* {company['address_en']}

🕒 *Working Hours:* 24/7
💼 *Account Manager:* Ahmed Gaber

✨ *We are here for you 24/7!*
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📞 اتصل الآن", url=f"tel:{company['phone']}"),
        types.InlineKeyboardButton("📧 أرسل بريد", url=f"mailto:{company['email']}")
    )
    markup.add(
        types.InlineKeyboardButton("🌐 زور موقعنا", url=company['website']),
        types.InlineKeyboardButton("🗺️ الموقع على الخريطة", url="https://maps.google.com/?q=Hurghada,Egypt")
    )
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

def send_quick_reply(chat_id, lang):
    if lang == "ar":
        text = "📍 الرجاء استخدام الأزرار في القائمة للتنقل"
    elif lang == "ru":
        text = "📍 Пожалуйста, используйте кнопки в меню для навигации"
    else:
        text = "📍 Please use the buttons in the menu to navigate"
    
    bot.send_message(chat_id, text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('inquiry_'))
def handle_inquiry(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    tour_id = int(call.data.replace('inquiry_', ''))
    
    lang = get_user_language(user_id)
    
    if lang == "ar":
        text = f"""
💬 *للاستفسار عن هذه الرحلة*

📞 يرجى التواصل معنا على:
{PROFESSIONAL_DATA['company']['phone']}

📧 أو عبر البريد الإلكتروني:
{PROFESSIONAL_DATA['company']['email']}

✨ سنكون سعداء بمساعدتك!
"""
    elif lang == "ru":
        text = f"""
💬 *Для запроса об этом туре*

📞 Пожалуйста, свяжитесь с нами:
{PROFESSIONAL_DATA['company']['phone']}

📧 Или по электронной почте:
{PROFESSIONAL_DATA['company']['email']}

✨ Мы будем рады помочь вам!
"""
    else:
        text = f"""
💬 *For inquiry about this tour*

📞 Please contact us at:
{PROFESSIONAL_DATA['company']['phone']}

📧 Or via email:
{PROFESSIONAL_DATA['company']['email']}

✨ We'll be happy to assist you!
"""
    
    bot.send_message(chat_id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

print("=" * 50)
print("✅ البوت الشامل المتكامل جاهز للعمل!")
print("🌍 يدعم 3 لغات: العربية والروسية والإنجليزية")
print("📧 نظام البريد الإلكتروني محدث ومضبوط")
print("🔐 إعدادات SMTP:")
print(f"   - المضيف: {EMAIL_CONFIG['smtp_server']}")
print(f"   - المنفذ: {EMAIL_CONFIG['port']}")
print(f"   - التشفير: SSL")
print(f"   - البريد: {EMAIL_CONFIG['sender_email']}")
print("🏆 نظام حجوزات متكامل مع تأكيد بالبريد")
print("📱 @Aht_88_bot")
print("=" * 50)

# بدء تشغيل البوت
if __name__ == "__main__":
    while True:
        try:
            print("🔄 بدء تشغيل البوت...")
            bot.polling(none_stop=True, timeout=30)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            print(f"🔄 إعادة الاتصال بعد خطأ: {e}")
            time.sleep(10)
