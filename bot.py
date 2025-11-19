import logging
import os
import sqlite3
import uuid
import re 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, filters, ConversationHandler,
)

# ሎግ ማዘጋጀት
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION & CONSTANTS ---
# እባክዎን ይህንን በራስዎ የUser ID ይቀይሩ!
ADMIN_USER_ID = 7023092861  # <--- የእርስዎ የቴሌግራም User ID እዚህ ይገባል!
TOKEN = "8463598785:AAEKNcAgBgNpMci0LWi4ZHDFw4MoV6E1gjI"
BOT_USERNAME = "Monlightprobot"
PHOTO_DIR = "user_photos"
DATABASE_NAME = "ethio_edu_users.db"

# Regular Expressions ለስልክ እና ለGmail ትክክለኛነት ማረጋገጫ
PHONE_REGEX = re.compile(r"^\+251\d{9}$")
GMAIL_SUFFIX = "@gmail.com"

# --- STATES ---
# ለምዝገባ
REGISTER_FULL_NAME, REGISTER_PHONE, REGISTER_ADDRESS, REGISTER_PHOTO, REGISTER_GMAIL, REGISTER_CONFIRM = range(6)
# ለመረጃ ማስተካከያ
MANAGE_DATA_MENU, MANAGE_PHONE, MANAGE_GMAIL, MANAGE_PHOTO = range(6, 10)
# ለአስተያየት (Feedback)
FEEDBACK_START, FEEDBACK_CONFIRM = range(10, 12)
# ለ Admin ተግባራት
ADMIN_MENU, ADMIN_BROADCAST_MSG, ADMIN_PRIVATE_MSG, ADMIN_GET_USER_ID = range(12, 16)


# --- Multilanguage Text Definitions ---
TEXT = {
    "am": {
        "welcome": "እንኳን ወደ Ethio Education ቦት በደህና መጡ!",
        "main_menu": "እባክዎን የሚፈልጉትን አገልግሎት ይምረጡ:",
        "register": "ለመመዝገብ",
        "manage_data": "መረጃ ማስተዳደር",
        "invite_friends": "ጓደኞችን መጋበዝ",
        "info": "የመገለጫ ካርድ",
        "language": "ቋንቋ መቀየር",
        "feedback": "አስተያየት ይስጡ", 
        "confirm": "አረጋግጣለሁ",
        "cancel": "እሰርዛለሁ",
        "back_to_menu": "ወደ ዋናው ገጽ ተመለስ",
        "reg_start": "ምዝገባውን ለመጀመር፣ እባክዎ **ሙሉ ስምዎን** ያስገቡ:",
        "ask_phone": "አሁን ደግሞ **ስልክ ቁጥርዎን** ያስገቡ (ለምሳሌ: +2519xxxxxxxx):",
        "ask_address": "የመኖሪያ **አድራሻዎን** ያስገቡ:",
        "ask_photo": "እባክዎ የሚያሳይ **ፎቶ** ይላኩ። (Skip ለማድረግ /skip ይጫኑ)",
        "ask_gmail": "ትክክለኛ **Gmail** አድራሻዎን ያስገቡ (ለምሳሌ: user@gmail.com፣ Skip ለማድረግ /skip ይጫኑ)",
        "phone_exists": "ይህ ስልክ ቁጥር አስቀድሞ ተመዝግቧል። ሌላ ቁጥር ይሞክሩ።",
        "gmail_exists": "ይህ Gmail አስቀድሞ ተመዝግሯል። ሌላ ጂሜይል ይሞክሩ።",
        "reg_review": "እባክዎ መረጃዎን ያረጋግጡ:",
        "reg_success": "✅ **ምዝገባው ተጠናቋል።** እንኳን ደስ አለዎት!",
        "reg_failed": "❌ ምዝገባው ተሰርዟል።",
        "not_registered": "🚫 ይቅርታ፣ ይህን አገልግሎት ለመጠቀም **መመዝገብ አለብዎት**። /start ብለው ይመዝገቡ።",
        "invitation_link": "የእርስዎ ልዩ የመጋበዣ ሊንክ:",
        "total_invites": "በእርስዎ ሊንክ የተመዘገቡ ሰዎች ቁጥር:",
        "manage_welcome": "የእርስዎ የመመዝገቢያ መረጃ (ከታች ያሉት)። የትኛውን ማስተካከል ይፈልጋሉ?",
        "manage_phone": "ስልክ ቁጥር አስተካክል",
        "manage_gmail": "Gmail አስተካክል",
        "manage_photo": "ፎቶ አስተካክል",
        "new_phone": "አዲሱን ስልክ ቁጥር (+251...) ያስገቡ:",
        "new_gmail": "አዲሱን Gmail (@gmail.com መጨረስ አለበት) ያስገቡ:",
        "new_photo": "አዲሱን ፎቶ ይላኩ:",
        "update_success": "✅ መረጃዎ በተሳካ ሁኔታ ተቀይሯል።",
        "lang_select": "ቋንቋዎን ይምረጡ:",
        "lang_changed": "ቋንቋዎ ወደ አማርኛ ተቀይሯል።",
        "skip_photo": "ፎቶ መላክ ተዘሏል።",
        "skip_gmail": "Gmail መላክ ተዘሏል።",
        "user_info": "የእርስዎ የመመዝገቢያ መረጃ",
        "view_card": "የመገለጫ ካርድ ይመልከቱ",
        "invalid_phone": "❌ ስልክ ቁጥሩ በ +251 መጀመር እና በትክክል 13 ቁምፊዎች መሆን አለበት።",
        "invalid_gmail": "❌ የGmail አድራሻው በትክክል @gmail.com መጨረስ አለበት።",
        # ለአስተያየት
        "ask_feedback": "እባክዎን መልዕክትዎን ወይም አስተያየትዎን ይጻፉ። (ከፍተኛ 512 ቁምፊዎች)",
        "feedback_review": "አስተያየትዎ ይህ ነው፤ ለማስረከብ 'አረጋግጣለሁ' ይጫኑ:",
        "feedback_success": "✅ አስተያየትዎ በተሳካ ሁኔታ ለ አስተዳዳሪው ተልኳል። እናመሰግናለን።",
        "feedback_failed": "❌ አስተያየትዎ ተሰርዟል።",
        # ለ Admin
        "admin_menu": "🤖 የአስተዳዳሪ (Admin) ሜኑ",
        "admin_broadcast": "መልዕክት ለሁሉም ተጠቃሚ መላክ",
        "admin_private": "መልዕክት ለአንድ ተጠቃሚ መላክ",
        "admin_ask_broadcast": "እባክዎ ለሁሉም ተጠቃሚዎች መላክ የሚፈልጉትን መልዕክት ያስገቡ (ማንኛውም ሚዲያም ይቻላል):",
        "admin_ask_user_id": "መልዕክቱን መላክ የሚፈልጉትን የተጠቃሚ User ID ያስገቡ:",
        "admin_ask_private": "እባክዎ ለአንድ ተጠቃሚ መላክ የሚፈልጉትን መልዕክት ያስገቡ (ማንኛውም ሚዲያም ይቻላል):",
        "admin_broadcast_success": "✅ መልዕክቱ ለሁሉም ተጠቃሚዎች ተልኳል።",
        "admin_private_success": "✅ መልዕክቱ ለተጠቃሚው ተልኳል።",
        "admin_invalid_id": "❌ የተጠቃሚ User ID ትክክል አይደለም።",
        "admin_not_found": "❌ የተጠቃሚ User ID በዳታቤዝ ውስጥ አልተገኘም።",
    },
    "en": {
        "welcome": "Welcome to the Ethio Education Bot!",
        "main_menu": "Please select the service you want:",
        "register": "Register",
        "manage_data": "Manage Data",
        "invite_friends": "Invite Friends",
        "info": "View Profile Card",
        "language": "Change Language",
        "feedback": "Give Feedback", 
        "confirm": "Confirm",
        "cancel": "Cancel",
        "back_to_menu": "Back to Main Menu",
        "reg_start": "To start registration, please enter your **Full Name**:",
        "ask_phone": "Now, enter your **Phone Number** (e.g., +2519xxxxxxxx):",
        "ask_address": "Enter your residential **Address**:",
        "ask_photo": "Please send a **Photo** of yourself. (Press /skip to skip)",
        "ask_gmail": "Enter your valid **Gmail** address (e.g., user@gmail.com, press /skip to skip)",
        "phone_exists": "This phone number is already registered. Try another.",
        "gmail_exists": "This Gmail is already registered. Try another.",
        "reg_review": "Please review your information:",
        "reg_success": "✅ **Registration complete.** Congratulations!",
        "reg_failed": "❌ Registration cancelled.",
        "not_registered": "🚫 Sorry, you must **register** to use this service. Use /start to register.",
        "invitation_link": "Your unique invitation link:",
        "total_invites": "Total users registered with your link:",
        "manage_welcome": "Your current registration data (shown below). Which one would you like to update?",
        "manage_phone": "Update Phone Number",
        "manage_gmail": "Update Gmail",
        "manage_photo": "Update Photo",
        "new_phone": "Enter the new phone number (+251...):",
        "new_gmail": "Enter the new Gmail (must end with @gmail.com):",
        "new_photo": "Send the new photo:",
        "update_success": "✅ Your information has been successfully updated.",
        "lang_select": "Select your language:",
        "lang_changed": "Your language has been changed to English.",
        "skip_photo": "Photo submission skipped.",
        "skip_gmail": "Gmail submission skipped.",
        "user_info": "Your Registration Information",
        "view_card": "View Profile Card",
        "invalid_phone": "❌ The phone number must start with +251 and be exactly 13 characters long.",
        "invalid_gmail": "❌ The Gmail address must end with @gmail.com.",
        # For Feedback
        "ask_feedback": "Please write your message or feedback. (Max 512 characters)",
        "feedback_review": "Your feedback is below; press 'Confirm' to submit:",
        "feedback_success": "✅ Your feedback has been successfully sent to the admin. Thank you.",
        "feedback_failed": "❌ Your feedback was cancelled.",
        # For Admin
        "admin_menu": "🤖 Admin Menu",
        "admin_broadcast": "Send Message to All Users",
        "admin_private": "Send Message to a Single User",
        "admin_ask_broadcast": "Please enter the message you want to send to all users (any media is also allowed):",
        "admin_ask_user_id": "Enter the User ID of the user you want to send the message to:",
        "admin_ask_private": "Please enter the message you want to send to the user (any media is also allowed):",
        "admin_broadcast_success": "✅ Message sent to all users.",
        "admin_private_success": "✅ Message sent to the user.",
        "admin_invalid_id": "❌ Invalid User ID.",
        "admin_not_found": "❌ User ID not found in the database.",
    }
}

# --- Database Functions ---

def init_db():
    """የ SQLite ዳታቤዝ ሰንጠረዥን ይፈጥራል።"""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone_number TEXT UNIQUE,
            address TEXT,
            gmail TEXT UNIQUE,
            photo_path TEXT,
            referral_code TEXT UNIQUE,
            invites_count INTEGER DEFAULT 0,
            registration_id TEXT UNIQUE,
            language TEXT DEFAULT 'am'
        )
    """)
    conn.commit()
    conn.close()

def get_user_data(user_id):
    """የተጠቃሚውን ሁሉንም መረጃ በuser_id ያገኛል።"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()
    conn.close()
    return data

def get_all_user_ids():
    """የሁሉንም ተጠቃሚዎች user_id ዝርዝር ያገኛል።"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    data = [row[0] for row in c.fetchall()]
    conn.close()
    return data

def register_user(data):
    """አዲስ ተጠቃሚን ይመዘግባል።"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        # Expected data: (user_id, full_name, phone_number, address, gmail, photo_path, referral_code, registration_id, language)
        # invites_count በ INSERT STATEMENT ውስጥ የለም ምክንያቱም DEFAULT 0 አለው
        c.execute("""
            INSERT INTO users (user_id, full_name, phone_number, address, gmail, photo_path, referral_code, registration_id, language) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Registration failed: {e}")
        return False
    finally:
        conn.close()

def update_user_field(user_id, field, value):
    """በተወሰነ መስክ ላይ መረጃን ያሻሽላል።"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Update failed (Integrity Error): {e}")
        # ለስልክ ወይም Gmail ሲሆን (Unique constraint)
        return False
    finally:
        conn.close()

def increment_invite_count(user_id):
    """የመጋበዝ ቆጣሪን ይጨምራል።"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET invites_count = invites_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user_data_by_referral_code(referral_code):
    """በ referral_code ተጠቅሞ የተጠቃሚውን መረጃ ያገኛል።"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    # SELECT user_id, referral_code
    c.execute("SELECT user_id, referral_code FROM users WHERE referral_code=?", (referral_code,))
    data = c.fetchone()
    conn.close()
    return data

# --- Utility Functions ---

async def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """የተጠቃሚውን ቋንቋ ከ context.user_data ወይም ከ Database ያገኛል።"""
    user_id = context._user_id
    if 'lang' not in context.user_data:
        data = get_user_data(user_id)
        # 9ኛ index (0-based) የቋንቋው መስክ ነው
        context.user_data['lang'] = data[9] if data and len(data) > 9 else 'am' 
    return context.user_data['lang']

def get_text(lang, key):
    """በተመረጠው ቋንቋ መልእክት ያገኛል።"""
    return TEXT.get(lang, TEXT['am']).get(key, TEXT['am'].get(key, f"<{key} not found>"))

async def download_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """ፎቶውን አውርዶ ፋይሉ የተቀመጠበትን መንገድ ይመልሳል።"""
    photo_file_id = update.message.photo[-1].file_id 
    try:
        file = await context.bot.get_file(photo_file_id)
        user_id = update.effective_user.id
        # የፋይሉን መንገድ Unique ለማድረግ ጊዜ እና የፋይል መታወቂያ እንጠቀማለን
        file_path = os.path.join(PHOTO_DIR, f"{user_id}_{photo_file_id[:8]}.jpg")
        await file.download_to_drive(file_path)
        return file_path
    except Exception as e:
        logger.error(f"Photo download failed: {e}")
        return "ERROR"

def format_user_details(user_data, lang, show_full=True):
    """የተጠቃሚውን ዝርዝር መረጃ በሚያምር ሁኔታ ያዘጋጃል።"""
    _ = lambda key: get_text(lang, key)
    
    if not user_data:
        return _("not_registered")
        
    # user_data structure: (user_id, full_name, phone_number, address, gmail, photo_path, referral_code, invites_count, registration_id, language)
    
    # ፎቶው ከተዘለለ N/A (Skipped) ይሆናል
    photo_status = '✅ የተላከ' if user_data[5] and user_data[5] != "N/A (Skipped)" else '❌ አልተላከም'
    lang_display = 'አማርኛ' if user_data[9] == 'am' else 'English' if user_data[9] == 'en' else user_data[9]

    message = (
        f"**👤 {_('user_info')}**\n"
        f"**----------------------------------------**\n"
        f"**ሙሉ ስም:** `{user_data[1]}`\n"
        f"**ስልክ ቁጥር:** `{user_data[2]}`\n"
        f"**አድራሻ:** `{user_data[3]}`\n"
        f"**Gmail:** `{user_data[4]}`\n"
        f"**የፎቶ ሁኔታ:** `{photo_status}`\n"
    )
    
    if show_full:
        message += (
            f"**----------------------------------------**\n"
            f"**የመመዝገቢያ ቁጥር:** `{user_data[8]}`\n"
            f"**ጋባዥ ብዛት:** `{user_data[7]}`\n"
            f"**የእርስዎ Referral Code:** `{user_data[6]}`\n"
            f"**ቋንቋ:** `{lang_display}`\n"
            f"**----------------------------------------**"
        )
        
    return message


# --- Handler Functions ---

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ዋናውን ሜኑ በInline Buttons ያሳያል።"""
    user = update.effective_user
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    # ተጠቃሚው መመዝገቡን ማረጋገጥ
    is_registered = get_user_data(user.id) is not None
    
    # Inline Buttons
    keyboard = [
        [InlineKeyboardButton(_("register"), callback_data="cmd_register")],
        [InlineKeyboardButton(_("manage_data"), callback_data="cmd_manage_data"),
         InlineKeyboardButton(_("invite_friends"), callback_data="cmd_invite_friends")],
        [InlineKeyboardButton(_("info"), callback_data="cmd_info"), 
         InlineKeyboardButton(_("language"), callback_data="cmd_language")],
        [InlineKeyboardButton(_("feedback"), callback_data="cmd_feedback")] 
    ]
    
    # ገና ያልተመዘገበ ከሆነ አንዳንድ አማራጮችን አጥፋ
    if not is_registered:
        # እነዚህ አማራጮች ሲጫኑ 'not_registered' መልዕክት እንዲሰጡ እንፈቅዳለን
        pass 

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = f"ሰላም *{user.first_name}*። {_('welcome')}" if lang == 'am' else f"Hi *{user.first_name}*. {_('welcome')}"
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                f"{welcome_text}\n\n{_('main_menu')}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception:
            # መልዕክቱ ከተሰረዘ ወይም ለመቀየር ካልተፈቀደ አዲስ እንልካለን
            await context.bot.send_message(
                chat_id=user.id,
                text=f"{welcome_text}\n\n{_('main_menu')}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

    else:
        await update.message.reply_text(
            f"{welcome_text}\n\n{_('main_menu')}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END if context.in_conversation else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ቦቱ ሲጀምር የሚጠራ ተግባር (ከ Referal Link ጋር መስራት ይችላል)"""
    user = update.effective_user
    
    await get_lang(context)
    
    # Referral Logic
    if context.args:
        referral_code = context.args[0]
        referrer_data = get_user_data_by_referral_code(referral_code)
        
        if referrer_data and get_user_data(user.id) is None:
            context.user_data['referrer_id'] = referrer_data[0] # referrer user_id
            logger.info(f"User {user.id} referred by {referrer_data[0]}")

    await show_main_menu(update, context)


# --- Registration Flow ---

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ምዝገባ ለመጀመር Inline Button ሲጫን ይጠራል"""
    query = update.callback_query
    await query.answer()
    
    if get_user_data(query.from_user.id):
        await query.edit_message_text("እርስዎ አስቀድመው ተመዝግበዋል።")
        return ConversationHandler.END

    lang = await get_lang(context)
    await query.edit_message_text(get_text(lang, "reg_start"))
    return REGISTER_FULL_NAME

async def reg_get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['full_name'] = update.message.text
    lang = await get_lang(context)
    await update.message.reply_text(get_text(lang, "ask_phone"))
    return REGISTER_PHONE

async def reg_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if not PHONE_REGEX.match(phone):
        await update.message.reply_text(_("invalid_phone"))
        return REGISTER_PHONE

    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE phone_number=?", (phone,))
    if c.fetchone():
        await update.message.reply_text(_("phone_exists"))
        conn.close()
        return REGISTER_PHONE
    conn.close()
    
    context.user_data['phone_number'] = phone
    await update.message.reply_text(_("ask_address"))
    return REGISTER_ADDRESS

async def reg_get_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['address'] = update.message.text
    lang = await get_lang(context)
    await update.message.reply_text(get_text(lang, "ask_photo"))
    return REGISTER_PHOTO

async def reg_get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if update.message.text and update.message.text.lower() == '/skip':
        context.user_data['photo_path'] = "N/A (Skipped)"
        await update.message.reply_text(_("skip_photo"))
    elif update.message.photo:
        context.user_data['photo_path'] = await download_photo(update, context)
    else:
        await update.message.reply_text(f"እባክዎ ትክክለኛ ፎቶ ይላኩ ወይም {_('skip_photo')}")
        return REGISTER_PHOTO
        
    await update.message.reply_text(_("ask_gmail"))
    return REGISTER_GMAIL

async def reg_get_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    gmail = ""
    
    if update.message.text and update.message.text.lower() == '/skip':
        gmail = "N/A (Skipped)"
        await update.message.reply_text(_("skip_gmail"))
    elif update.message.text:
        gmail = update.message.text.strip()
        
        if not gmail.endswith(GMAIL_SUFFIX):
            await update.message.reply_text(_("invalid_gmail"))
            return REGISTER_GMAIL
            
        conn = sqlite3.connect(DATABASE_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE gmail=?", (gmail,))
        if c.fetchone():
            await update.message.reply_text(_("gmail_exists"))
            conn.close()
            return REGISTER_GMAIL 
        conn.close()
    else:
        await update.message.reply_text(f"እባክዎ ትክክለኛ Gmail ያስገቡ ወይም {_('skip_gmail')}")
        return REGISTER_GMAIL
        
    context.user_data['gmail'] = gmail
    
    return await reg_review_and_confirm(update, context)

async def reg_review_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """የመጨረሻ ማረጋገጫ በInline Button"""
    user_data = context.user_data
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    review_text = (
        _("reg_review") + "\n"
        f"**1. ሙሉ ስም:** `{user_data.get('full_name')}`\n"
        f"**2. ስልክ ቁጥር:** `{user_data.get('phone_number')}`\n"
        f"**3. አድራሻ:** `{user_data.get('address')}`\n"
        f"**4. Gmail:** `{user_data.get('gmail')}`\n"
        f"**5. ፎቶ:** {'✅ ተልኳል' if user_data.get('photo_path') != 'N/A (Skipped)' else '❌ አልተላከም'}"
    )

    keyboard = [[InlineKeyboardButton(_("confirm"), callback_data="reg_confirm"), 
                 InlineKeyboardButton(_("cancel"), callback_data="reg_cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # መልዕክቱ ከCallback (ለምሳሌ /skip) ካልመጣ
    if update.message:
        await update.message.reply_text(review_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        # ለምሳሌ /skip የሚል መልዕክት ከሌለ
        await context.bot.send_message(chat_id=update.effective_chat.id, text=review_text, reply_markup=reply_markup, parse_mode="Markdown")

    return REGISTER_CONFIRM

async def reg_handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ምዝገባን ማጠናቀቅ ወይም መሰረዝ"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_data = context.user_data
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    if query.data == "reg_confirm":
        # 16 ቁምፊ ቁጥር እና Referral Code መፍጠር
        reg_id = str(uuid.uuid4()).replace('-', '')[:16].upper() 
        referral_code = str(uuid.uuid4()).replace('-', '')[:8].upper()
        
        # የ invites_count (0) ዋጋን ከዝርዝሩ ላይ አስወግደናል ምክንያቱም በዳታቤዝ ላይ DEFAULT 0 አለው።
        # 9 ዋጋዎች: (user_id, full_name, phone_number, address, gmail, photo_path, referral_code, registration_id, language)
        user_db_data = (
            user.id, user_data['full_name'], user_data['phone_number'], user_data['address'], 
            user_data['gmail'], user_data['photo_path'], referral_code, reg_id, lang
        )
        
        if register_user(user_db_data):
            # Referral Count መጨመር (ከ Referral Link ከመጣ)
            if 'referrer_id' in context.user_data:
                increment_invite_count(context.user_data['referrer_id'])

            # ለተጠቃሚው የመጨረሻ መልእክት መስጠት
            invitation_link = f"https://t.me/{BOT_USERNAME}?start={referral_code}"
            
            final_message = (
                _("reg_success") + "\n\n"
                f"**የመመዝገቢያ ቁጥርዎ:** `{reg_id}`\n\n"
                f"**የእርስዎ የመጋበዣ ሊንክ:**\n`{invitation_link}`\n"
            )
            await query.edit_message_text(final_message, parse_mode="Markdown")
            
            return await show_main_menu(update, context)

        else:
            await query.edit_message_text("ስህተት ተከስቷል። ምዝገባው አልተሳካም። (ስልክ ወይም Gmail አስቀድሞ ተመዝግቧል)")
            return ConversationHandler.END
            
    elif query.data == "reg_cancel":
        context.user_data.clear()
        await query.edit_message_text(_("reg_failed"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        return ConversationHandler.END

# --- Invitation and Info (Profile Card) ---

async def show_invitation_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """የመጋበዣ ሊንክ እና የጋበዙትን ሰዎች ቁጥር ያሳያል።"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    user_data = get_user_data(user.id)
    if not user_data:
        await query.edit_message_text(_("not_registered"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        return

    # user_data[6] = referral_code, user_data[7] = invites_count
    referral_code = user_data[6]
    invites_count = user_data[7]
    invitation_link = f"https://t.me/{BOT_USERNAME}?start={referral_code}"

    message = (
        f"**🎉 {_('invite_friends')}**\n"
        f"**----------------------------------------**\n"
        f"*{_('invitation_link')}*\n"
        f"`{invitation_link}`\n\n"
        f"*{_('total_invites')}* `{invites_count}`"
    )
    
    keyboard = [[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- (በ bot.py ውስጥ ከ574ኛው መስመር አካባቢ) ---
async def show_profile_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """የተጠቃሚውን መረጃ በCard መልክ ያሳያል (ፎቶ ካለ በፎቶ Caption)።"""
    query = update.callback_query
    # የ"እባክዎ ይጠብቁ" የሚለው መልዕክት ለተጠቃሚው ወዲያው እንዲታይ እናደርጋለን
    try:
        await query.answer() 
        await query.edit_message_text("የመገለጫ ካርድ ይመልከቱ\nእባክዎ ትንሽ ይጠብቁ...")
    except Exception:
        # መልዕክቱ አስቀድሞ ተስተካክሎ ከሆነ ወይም ስህተት ከተፈጠረ ችላ እንለዋለን
        pass 

    user = query.from_user
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    user_data = get_user_data(user.id)
    
    if not user_data:
        # ስህተት ከተፈጠረ መልዕክቱን አስተካክሎ ይመልሳል
        await context.bot.send_message(user.id, _("not_registered"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        return
        
    caption = format_user_details(user_data, lang, show_full=True)
    
    # user_data[5] የፎቶ መንገድ ነው
    photo_path = user_data[5] if user_data[5] and user_data[5] != "N/A (Skipped)" else None
    
    is_photo_sent = False
    
    # 2. የመገለጫ ካርዱን መላክ
    if photo_path and os.path.exists(photo_path):
        try:
            # ፋይሉን በቢናሪ ሞድ (rb) ከፍተን እንልካለን
            with open(photo_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=InputFile(photo_file), # የፋይሉን ይዘት እንልካለን
                    caption=caption,
                    parse_mode="Markdown",
                )
            is_photo_sent = True
        except Exception as e:
            # ፎቶ የመላክ ስህተት ከተፈጠረ ወደ ጽሑፍ መላክ እንቀይራለን
            logger.error(f"Failed to send user photo {photo_path}: {e}")
            pass 
        
    # ፎቶ ካልተላከ (ወይም ፎቶ ከሌለ/በመላክ ላይ ስህተት ከተፈጠረ)
    if not is_photo_sent:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"{_('view_card')}\n\n{caption}", 
            parse_mode="Markdown", 
        )
        
    # 3. ወደ ዋናው ሜኑ የሚመልስ ቁልፍ ያለው መልዕክት መላክ
    keyboard = [[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user.id,
        text=f"{_('view_card')} በተሳካ ሁኔታ ተልኳል።\nእባክዎ ወደ ዋናው ገጽ ለመመለስ ቁልፉን ይጫኑ።",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# --- Language Selection ---

async def show_language_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ቋንቋ የመምረጫ ሜኑ ያሳያል።"""
    query = update.callback_query
    await query.answer()
    
    # የአሁኑን ቋንቋ ለማግኘት
    current_lang = await get_lang(context)
    
    # ቋንቋው ስላልተመረጠ የአማርኛውን 'back_to_menu' እንጠቀማለን
    keyboard = [
        [InlineKeyboardButton(f"አማርኛ (Amharic) {'✅' if current_lang == 'am' else ''}", callback_data="lang_am")],
        [InlineKeyboardButton(f"English {'✅' if current_lang == 'en' else ''}", callback_data="lang_en")],
        [InlineKeyboardButton(get_text(current_lang, 'back_to_menu'), callback_data="cmd_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(get_text(current_lang, 'lang_select'), reply_markup=reply_markup)

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ቋንቋን ይቀይራል እና ዳታቤዝ ላይ ያሻሽላል።"""
    query = update.callback_query
    await query.answer()
    
    new_lang = query.data.split('_')[1]
    
    # 1. በ context ላይ ማሻሻል
    context.user_data['lang'] = new_lang
    
    # 2. በ Database ላይ ማሻሻል (ተመዝግቦ ከሆነ)
    if get_user_data(query.from_user.id):
        update_user_field(query.from_user.id, 'language', new_lang)
    
    lang = new_lang # አዲሱን ቋንቋ ተጠቀም
    _ = lambda key: get_text(lang, key)
    
    await query.edit_message_text(_("lang_changed"), 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))

# --- Data Management Flow ---

async def start_data_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """መረጃ ማስተካከያ ሜኑ ያሳያል።"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    user_data = get_user_data(user.id)
    if not user_data:
        await query.edit_message_text(_("not_registered"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        return ConversationHandler.END

    info_display = format_user_details(user_data, lang, show_full=False)
    
    keyboard = [
        [InlineKeyboardButton(_("manage_phone"), callback_data="manage_phone")],
        [InlineKeyboardButton(_("manage_gmail"), callback_data="manage_gmail")],
        [InlineKeyboardButton(_("manage_photo"), callback_data="manage_photo")],
        [InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"{info_display}\n\n**{_('manage_welcome')}**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return MANAGE_DATA_MENU

async def handle_manage_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """የማስተዳደር ሜኑ ምርጫን ያካሂዳል።"""
    query = update.callback_query
    await query.answer()
    selection = query.data
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if selection == "manage_phone":
        await query.edit_message_text(_("new_phone"))
        return MANAGE_PHONE
    elif selection == "manage_gmail":
        await query.edit_message_text(_("new_gmail"))
        return MANAGE_GMAIL
    elif selection == "manage_photo":
        await query.edit_message_text(_("new_photo"))
        return MANAGE_PHOTO
    
    # ይህ ሲስተካከል ወደ MANAGE_DATA_MENU መመለስ የለበትም፣ አዲስ መልዕክት መላክ አለበት
    if selection == "cmd_menu":
        await show_main_menu(update, context)
        return ConversationHandler.END

    return MANAGE_DATA_MENU

async def manage_update_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_phone = update.message.text.strip()
    user_id = update.effective_user.id
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if not PHONE_REGEX.match(new_phone):
        await update.message.reply_text(_("invalid_phone"))
        return MANAGE_PHONE

    if not update_user_field(user_id, 'phone_number', new_phone):
        await update.message.reply_text(_("phone_exists"))
        return MANAGE_PHONE
        
    await update.message.reply_text(_("update_success"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
    return ConversationHandler.END

async def manage_update_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_gmail = update.message.text.strip()
    user_id = update.effective_user.id
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if not new_gmail.endswith(GMAIL_SUFFIX):
        await update.message.reply_text(_("invalid_gmail"))
        return MANAGE_GMAIL
        
    if not update_user_field(user_id, 'gmail', new_gmail):
        await update.message.reply_text(_("gmail_exists"))
        return MANAGE_GMAIL
        
    await update.message.reply_text(_("update_success"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
    return ConversationHandler.END

async def manage_update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if update.message.photo:
        # TODO: አሮጌውን ፎቶ መሰረዝ እዚህ ይገባል
        photo_path = await download_photo(update, context)
        update_user_field(user_id, 'photo_path', photo_path)
        await update.message.reply_text(_("update_success"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"እባክዎ **ትክክለኛ ፎቶ** ይላኩ።")
        return MANAGE_PHOTO

# --- Feedback Flow ---

async def start_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """አስተያየት የመስጠት ሂደትን ይጀምራል።"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    if not get_user_data(user.id):
        await query.edit_message_text(_("not_registered"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        return ConversationHandler.END

    await query.edit_message_text(_("ask_feedback"))
    return FEEDBACK_START

async def get_feedback_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """የተጠቃሚውን መልዕክት ተቀብሎ ለማረጋገጥ ያቀርባል።"""
    user_message = update.message.text
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    if not user_message or len(user_message) > 512:
        await update.message.reply_text(get_text(lang, "ask_feedback"))
        return FEEDBACK_START

    context.user_data['feedback_message'] = user_message
    
    review_text = f"**{_('feedback_review')}**\n\n`{user_message}`"
    
    keyboard = [[InlineKeyboardButton(_("confirm"), callback_data="fb_confirm"), 
                 InlineKeyboardButton(_("cancel"), callback_data="fb_cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(review_text, reply_markup=reply_markup, parse_mode="Markdown")
    return FEEDBACK_CONFIRM

async def handle_feedback_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """አስተያየቱን ለAdmin ይልካል ወይም ይሰርዛል።"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    if query.data == "fb_confirm":
        feedback_message = context.user_data['feedback_message']
        
        # ለAdmin መላክ
        admin_message = (
            f"**📩 አዲስ የተጠቃሚ አስተያየት (Feedback)**\n"
            f"**ተጠቃሚ ID:** `{user.id}`\n"
            f"**ተጠቃሚ ስም:** `{user.first_name} {user.last_name or ''}` (@{user.username or 'N/A'})\n"
            f"**----------------------------------------**\n"
            f"{feedback_message}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message, parse_mode="Markdown")
            await query.edit_message_text(_("feedback_success"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
        except Exception as e:
            logger.error(f"Failed to send feedback to admin: {e}")
            await query.edit_message_text("❌ አስተያየቱን ወደ አስተዳዳሪው መላክ አልተቻለም።", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
            
    elif query.data == "fb_cancel":
        await query.edit_message_text(_("feedback_failed"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))

    context.user_data.pop('feedback_message', None)
    return ConversationHandler.END

# --- Admin Flow ---

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ለAdmin ብቻ የሚሆን ሜኑ ያሳያል።"""
    user_id = update.effective_user.id
    
    # የ Admin መሆኑን ማረጋገጫ
    if user_id != ADMIN_USER_ID:
        if update.message:
            await update.message.reply_text("🚫 ይቅርታ፣ ይህ ትእዛዝ ለ አስተዳዳሪዎች ብቻ ነው።")
        return ConversationHandler.END

    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    keyboard = [
        [InlineKeyboardButton(_("admin_broadcast"), callback_data="admin_broadcast")],
        [InlineKeyboardButton(_("admin_private"), callback_data="admin_private")],
        [InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # መልዕክቱ ከኮማንድ ከመጣ (መጀመሪያ ሲጀምር) ወይም ከCallback (ከAdmin Menu ሲመለስ)
    if update.callback_query:
        await update.callback_query.edit_message_text(_("admin_menu"), reply_markup=reply_markup)
    else:
        await update.message.reply_text(_("admin_menu"), reply_markup=reply_markup)
        
    return ADMIN_MENU

async def handle_admin_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """የAdmin ሜኑ ምርጫን ያካሂዳል።"""
    query = update.callback_query
    await query.answer()
    selection = query.data
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    if selection == "admin_broadcast":
        await query.edit_message_text(_("admin_ask_broadcast"))
        return ADMIN_BROADCAST_MSG
    elif selection == "admin_private":
        await query.edit_message_text(_("admin_ask_user_id"))
        return ADMIN_GET_USER_ID
    
    # ወደ ዋናው ሜኑ ሲመለስ ውይይቱን ያቋርጣል
    if selection == "cmd_menu":
        await show_main_menu(update, context)
        return ConversationHandler.END
        
    return ADMIN_MENU

async def admin_get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """መልዕክት የሚላክለት ተጠቃሚ User ID ይቀበላል።"""
    user_id_str = update.message.text.strip()
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)

    try:
        target_user_id = int(user_id_str)
        if not get_user_data(target_user_id):
             await update.message.reply_text(_("admin_not_found"))
             return ADMIN_GET_USER_ID

        context.user_data['target_user_id'] = target_user_id
        await update.message.reply_text(_("admin_ask_private"))
        return ADMIN_PRIVATE_MSG
    except ValueError:
        await update.message.reply_text(_("admin_invalid_id"))
        return ADMIN_GET_USER_ID

async def admin_handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """መልዕክቱን ለሁሉም ተጠቃሚዎች ይልካል።"""
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    all_user_ids = get_all_user_ids()
    sent_count = 0
    
    message = update.message
    
    for user_id in all_user_ids:
        try:
            # መልዕክቱን መገልበጥ
            await message.copy(chat_id=user_id)
            sent_count += 1
        except Exception as e:
            logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
            
    await update.message.reply_text(f"{_('admin_broadcast_success')} ({sent_count}/{len(all_user_ids)} ተልኳል)")
    return ConversationHandler.END

async def admin_handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """መልዕክቱን ለአንድ ተጠቃሚ ይልካል።"""
    target_user_id = context.user_data.get('target_user_id')
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    message = update.message
    
    try:
        # መልዕክቱን መገልበጥ
        await message.copy(chat_id=target_user_id)
        await update.message.reply_text(f"{_('admin_private_success')} (ለ {target_user_id} ተልኳል)")
    except Exception as e:
        logger.error(f"Failed to send private message to user {target_user_id}: {e}")
        await update.message.reply_text(f"❌ መልዕክቱ ሊላክ አልቻለም። (ስህተት: {e})")
        
    context.user_data.pop('target_user_id', None)
    return ConversationHandler.END

# --- Fallback and Error Handlers ---

async def general_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ውይይቱን አቋርጦ ወደ ዋናው ሜኑ ይመልሳል።"""
    user = update.effective_user
    context.user_data.clear()
    logger.info(f"User {user.id} cancelled the conversation.")
    
    lang = await get_lang(context)
    _ = lambda key: get_text(lang, key)
    
    # መልዕክቱን በአዲስ መልክ መላክ
    if update.callback_query:
        await update.callback_query.answer()
        await context.bot.send_message(
            chat_id=user.id,
            text=f"**❌ {_('reg_failed')}**\n{_('back_to_menu')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]])
        )
    else:
        await update.message.reply_text(
            f"**❌ {_('reg_failed')}**\n{_('back_to_menu')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]])
        )
        
    return ConversationHandler.END

async def general_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ላልተጠበቁ መልእክቶች መልስ ይሰጣል።"""
    if update.message:
        lang = await get_lang(context)
        _ = lambda key: get_text(lang, key)
        # አዲስ መልዕክት በመላክ ወደ ዋናው ሜኑ መመለሻ ቁልፍ መስጠት
        await update.message.reply_text(f"እባክዎ ትክክለኛውን ምርጫ ወይም ትዕዛዝ ይጠቀሙ።", 
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_("back_to_menu"), callback_data="cmd_menu")]]))
    
    return ConversationHandler.END 

# --- Main Logic ---

def main() -> None:
    """ቦቱን የሚያስጀምር ዋና ተግባር።"""
    
    # ዳታቤዙን እና የፎቶ ማህደሩን ማዘጋጀት
    init_db()

    application = ApplicationBuilder().token(TOKEN).build()
    
    # --- Conversation Handlers ---
    
    # 1. የምዝገባ ውይይት
    reg_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration, pattern="^cmd_register$")],
        states={
            REGISTER_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_full_name)],
            REGISTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_phone)],
            REGISTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_address)],
            REGISTER_PHOTO: [
                MessageHandler(filters.PHOTO | filters.Regex('^/skip$'), reg_get_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_photo) 
            ],
            REGISTER_GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_gmail)],
            REGISTER_CONFIRM: [CallbackQueryHandler(reg_handle_confirmation, pattern="^reg_")],
        },
        fallbacks=[CommandHandler("cancel", general_cancel), MessageHandler(filters.COMMAND, general_cancel)],
    )

    # 2. መረጃ ማስተዳደር ውይይት
    manage_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_data_management, pattern="^cmd_manage_data$")],
        states={
            MANAGE_DATA_MENU: [CallbackQueryHandler(handle_manage_menu_selection, pattern="^manage_")],
            MANAGE_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, manage_update_phone)],
            MANAGE_GMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, manage_update_gmail)],
            MANAGE_PHOTO: [MessageHandler(filters.PHOTO, manage_update_photo)],
        },
        fallbacks=[CommandHandler("cancel", general_cancel), MessageHandler(filters.COMMAND, general_cancel)],
    )
    
    # 3. የአስተያየት ውይይት
    feedback_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_feedback, pattern="^cmd_feedback$")],
        states={
            FEEDBACK_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_feedback_message)],
            FEEDBACK_CONFIRM: [CallbackQueryHandler(handle_feedback_confirmation, pattern="^fb_")],
        },
        fallbacks=[CommandHandler("cancel", general_cancel), MessageHandler(filters.COMMAND, general_cancel)],
    )
    
    # 4. የ Admin ውይይት
    admin_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_MENU: [CallbackQueryHandler(handle_admin_menu_selection, pattern="^admin_|^cmd_menu$")],
            ADMIN_BROADCAST_MSG: [MessageHandler(filters.ALL, admin_handle_broadcast_message)],
            ADMIN_GET_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_get_user_id)],
            ADMIN_PRIVATE_MSG: [MessageHandler(filters.ALL, admin_handle_private_message)],
        },
        fallbacks=[CommandHandler("cancel", general_cancel)],
    )

    # --- General Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(reg_handler)
    application.add_handler(manage_handler)
    application.add_handler(feedback_handler)
    application.add_handler(admin_handler)
    
    # ቋንቋ መቀየር (ከውይይት ውጪ)
    application.add_handler(CallbackQueryHandler(show_language_options, pattern="^cmd_language$"))
    application.add_handler(CallbackQueryHandler(change_language, pattern="^lang_"))
    
    # ዋና ሜኑ መመለስ
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="^cmd_menu$"))
    
    # የጋበዙት ሰዎች እና መረጃ
    application.add_handler(CallbackQueryHandler(show_invitation_info, pattern="^cmd_invite_friends$"))
    application.add_handler(CallbackQueryHandler(show_profile_card, pattern="^cmd_info$")) # ለCard Display
    
    # ያልታወቁ መልእክቶች
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, general_fallback))

    print("Ethio Education Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
