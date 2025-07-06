import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
)
import json
import os
from datetime import datetime
import re
from persiantools import characters

# تنظیمات اولیه
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# اطلاعات ثابت
TOKEN = "7990594193:AAH6I2BW5ZAwuc9J0g3kgIOzIVx346j3x6U"
ADMIN_ID = 378486866
ADMIN_GROUP_ID = -1002859501160  # تغییر آیدی گروه ادمین برای آرشیو
SUPPORT_PHONE = "09138895464"
SUPPORT_USERNAME = "@Pwsupport"
SHOP_URL = "https://www.persianway.shop"
INSTAGRAM = "https://www.instagram.com/Persianway.shop"
WHATSAPP = "https://wa.me/989138895464"
COMMISSION_RATE = 530000  # پورسانت به تومان
COMMISSION_THRESHOLD = 6000000  # حداقل خرید برای دریافت پورسانت (6 میلیون تومان)
REFERRAL_PURCHASE_VALUE = 3000000  # ارزش هر معرفی موفق (3 میلیون تومان)
REFERRAL_COMMISSION_RATE = 0.09  # 9% از خرید زیرمجموعه‌ها

# حالت‌های مکالمه
(
    GET_NAME, GET_FATHER_NAME, GET_NATIONAL_ID,
    GET_ADDRESS, GET_POSTAL_CODE, GET_PHONE,
    VERIFY_CODE, ORDER_CODE, INVITE_1, INVITE_2,
    BANK_CARD, EDIT_ADDRESS, EDIT_POSTAL_CODE,
    DIRECT_INVITE, WITHDRAW_AMOUNT, COMPLETE_COMMISSION,
    DIRECT_NAME, DIRECT_FATHER_NAME, DIRECT_NATIONAL_ID,
    DIRECT_ADDRESS, DIRECT_POSTAL_CODE, DIRECT_PHONE,
    DIRECT_ORDER_CODE, EDIT_USER_DATA, HELP
) = range(25)

DATA_FILE = "users_data.json"

def load_data():
    """بارگذاری داده‌های کاربران از فایل JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {
                    "users": {},
                    "pending_approvals": {},
                    "commissions": {},
                    "referrals": {},
                    "purchases": {},
                    "direct_invites": {},
                    "admin_messages": {},
                    "pending_invites": {}
                }
    return {
        "users": {},
        "pending_approvals": {},
        "commissions": {},
        "referrals": {},
        "purchases": {},
        "direct_invites": {},
        "admin_messages": {},
        "pending_invites": {}
    }

def save_data(data):
    """ذخیره داده‌های کاربران در فایل JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def normalize_phone(phone):
    """نرمال‌سازی شماره تلفن"""
    phone = normalize_number(phone)
    
    if phone.startswith('0') and len(phone) == 11:
        return phone
    if phone.startswith('98') and len(phone) == 12:
        return '0' + phone[2:]
    if phone.startswith('+98') and len(phone) == 13:
        return '0' + phone[3:]
    return phone

def normalize_number(number):
    """نرمال‌سازی اعداد (حذف کاراکترهای غیرعددی و تبدیل به انگلیسی)"""
    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    arabic_to_english = str.maketrans('٠١٢٣٤٥٦۷۸۹', '0123456789')
    
    number = re.sub(r'[^0-9۰-۹٠-٩]', '', str(number))
    number = number.translate(persian_to_english)
    number = number.translate(arabic_to_english)
    return number

async def show_main_menu(chat_id, context, message=None, first_time=False):
    """نمایش منوی اصلی کاربری"""
    keyboard = [
        [InlineKeyboardButton("🛒 ثبت شماره سفارش", callback_data="complete_commission")],
        [
            InlineKeyboardButton("👥 معرفی دوستان", callback_data="invite_friends"),
            InlineKeyboardButton("📊 پروفایل من", callback_data="profile")
        ],
        [
            InlineKeyboardButton("📈 زیرمجموعه‌ها", callback_data="subsets"),
            InlineKeyboardButton("💰 پورسانت‌ها", callback_data="my_commissions")
        ],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🌟 به ربات کسب درآمد لایمن خوش آمدید! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:" if first_time else "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    
    if message:
        await message.edit_text(text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت بازگشت به منوی اصلی"""
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            try:
                await context.bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)
            except:
                pass
        else:
            try:
                await context.bot.delete_message(chat_id=update.message.from_user.id, message_id=update.message.message_id)
            except:
                pass
        
        user_id = str(update.effective_user.id)
        data = load_data()
        
        if user_id in data["users"]:
            if data["users"][user_id].get("status") == "active":
                await show_main_menu(user_id, context, first_time=False)
                return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error in back_handler: {str(e)}")
        await start(update, context)

async def track_message(user_id: str, message_type: str, message_id: int = None):
    """ردیابی پیام‌های ارسالی به کاربر"""
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if "last_messages" not in user_data:
        user_data["last_messages"] = []
    
    if user_data["last_messages"] and user_data["last_messages"][-1]["type"] == message_type:
        return
    
    user_data["last_messages"].append({
        "type": message_type,
        "message_id": message_id
    })
    
    if len(user_data["last_messages"]) > 5:
        user_data["last_messages"] = user_data["last_messages"][-5:]
    
    data["users"][user_id] = user_data
    save_data(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع ربات و ثبت نام کاربر جدید"""
    user = update.effective_user
    user_id = str(user.id)
    data = load_data()
    
    if user_id in data["users"]:
        if data["users"][user_id].get("status") == "active":
            await show_main_menu(user_id, context, first_time=False)
            return ConversationHandler.END
        else:
            status = data["users"][user_id].get("status")
            if status == "pending_registration":
                await update.message.reply_text("✅ اطلاعات شما دریافت شده و در حال بررسی است. لطفاً منتظر بمانید.")
            elif status == "pending_verification":
                await update.message.reply_text(
                    "لطفاً کد تأیید ارسال شده به شماره همراه خود را وارد کنید:"
                )
                return VERIFY_CODE
            elif status == "pending_order":
                await update.message.reply_text(
                    "🎉 تایید هویت شما با موفقیت انجام شد.\n\n"
                    "برای فعال‌سازی حساب، کافیست حداقل 3 میلیون تومان یا بیشتر از محصولات برند لایمن یا مالیمن در فروشگاه آنلاین خرید و شماره سفارشتان را اینجا ارسال کنید.\n\n"
                    f"🛍️ آدرس فروشگاه: {SHOP_URL}\n\n"
                    "پس از خرید، لطفاً شماره سفارش خود را اینجا وارد کنید:"
                )
                return ORDER_CODE
            else:
                await update.message.reply_text("⚠️ حساب شما فعال نیست. لطفاً با پشتیبانی تماس بگیرید.")
            return ConversationHandler.END
    
    if context.args and len(context.args) > 0:
        referrer_id = context.args[0]
        if referrer_id != user_id and referrer_id in data["users"]:
            context.user_data["referrer"] = referrer_id
    
    await update.message.reply_text(
        "🌟 سلام! به ربات کسب درآمد لایمن خوش آمدید.\n\n"
        "برای شروع ثبت نام، لطفاً نام و نام خانوادگی خود را وارد کنید:"
    )
    await track_message(user_id, "registration")
    return GET_NAME

async def resend_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال مجدد کد تأیید"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    await query.edit_message_text(
        "لطفاً کد تأیید ارسال شده به شماره همراه خود را وارد کنید:"
    )
    return VERIFY_CODE

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت نام کاربر"""
    context.user_data["name"] = update.message.text
    await update.message.reply_text("👨‍👦 لطفاً نام پدر خود را وارد کنید:")
    await track_message(str(update.effective_user.id), "registration")
    return GET_FATHER_NAME

async def get_father_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت نام پدر کاربر"""
    context.user_data["father_name"] = update.message.text
    await update.message.reply_text("🆔 لطفاً کد ملی خود را وارد کنید (10 رقم):")
    await track_message(str(update.effective_user.id), "registration")
    return GET_NATIONAL_ID

async def get_national_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت کد ملی کاربر"""
    national_id = normalize_number(update.message.text)
    if len(national_id) != 10:
        await update.message.reply_text("❌ کد ملی باید 10 رقم باشد! لطفاً مجدداً وارد کنید:")
        return GET_NATIONAL_ID
    
    context.user_data["national_id"] = national_id
    await update.message.reply_text("🏠 لطفاً آدرس کامل خود را وارد کنید:")
    await track_message(str(update.effective_user.id), "registration")
    return GET_ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت آدرس کاربر"""
    context.user_data["address"] = update.message.text
    await update.message.reply_text("📮 لطفاً کد پستی خود را وارد کنید (10 رقم):")
    await track_message(str(update.effective_user.id), "registration")
    return GET_POSTAL_CODE

async def get_postal_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت کد پستی کاربر"""
    postal_code = normalize_number(update.message.text)
    if len(postal_code) != 10:
        await update.message.reply_text("❌ کد پستی باید 10 رقم باشد! لطفاً مجدداً وارد کنید:")
        return GET_POSTAL_CODE
    
    context.user_data["postal_code"] = postal_code
    await update.message.reply_text("📱 لطفاً شماره موبایل خود را وارد کنید (11 رقم):")
    await track_message(str(update.effective_user.id), "registration")
    return GET_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت شماره تلفن کاربر و ثبت نهایی اطلاعات"""
    try:
        phone = normalize_phone(update.message.text)
        if len(phone) != 11:
            await update.message.reply_text("❌ شماره موبایل باید 11 رقم باشد! لطفاً مجدداً وارد کنید:")
            return GET_PHONE
        
        user_id = str(update.effective_user.id)
        context.user_data["phone"] = phone
        context.user_data["registration_date"] = str(datetime.now())
        context.user_data["status"] = "pending_registration"
        
        data = load_data()
        data["users"][user_id] = context.user_data.copy()
        
        if "referrer" in context.user_data:
            referrer_id = context.user_data["referrer"]

            if referrer_id not in data["referrals"]:
                data["referrals"][referrer_id] = []
            data["referrals"][referrer_id].append(user_id)
        
        admin_text = (
            f"📝 درخواست ثبت‌نام جدید\n\n"
            f"👤 نام: {context.user_data['name']}\n"
            f"👨‍👦 نام پدر: {context.user_data['father_name']}\n"
            f"🆔 کد ملی: {context.user_data['national_id']}\n"
            f"🏠 آدرس: {context.user_data['address']}\n"
            f"📮 کد پستی: {context.user_data['postal_code']}\n"
            f"📱 شماره موبایل: {phone}\n"
            f"🆔 آیدی کاربر: {user_id}"
        )
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text
        )
        
        group_message = await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_text
        )
        
        data["pending_approvals"][str(admin_message.message_id)] = {
            "type": "registration",
            "user_id": user_id
        }
        
        data["admin_messages"][str(admin_message.message_id)] = {
            "group_message_id": group_message.message_id,
            "user_id": user_id,
            "type": "registration"
        }
        
        save_data(data)
        
        await update.message.reply_text(
            "✅ اطلاعات شما ثبت شد و برای تأیید به ادمین ارسال شد.\n"
            "پس از تأیید ادمین، ادامه مراحل به شما اطلاع داده خواهد شد."
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"خطا در ثبت اطلاعات: {str(e)}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
        return ConversationHandler.END

async def verify_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید کد ارسالی به کاربر"""
    try:
        user_id = str(update.effective_user.id)
        verification_code = update.message.text
        
        # Check if input is a valid number
        if not verification_code.isdigit():
            await update.message.reply_text(
                "❌ کد تأیید باید عددی باشد! لطفاً مجدداً وارد کنید:"
            )
            return VERIFY_CODE
            
        data = load_data()
        user_data = data["users"].get(user_id, {})
                
        admin_text = (
            f"🔢 کد تأیید کاربر\n\n"
            f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
            f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
            f"🆔 آیدی: {user_id}\n"
            f"🔢 کد وارد شده: {verification_code}"
        )
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text
        )
        
        group_message = await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_text
        )
        
        data["pending_approvals"][str(admin_message.message_id)] = {
            "type": "verification",
            "user_id": user_id
        }
        
        data["admin_messages"][str(admin_message.message_id)] = {
            "group_message_id": group_message.message_id,
            "user_id": user_id,
            "type": "verification"
        }
        
        save_data(data)
        
        await update.message.reply_text("✅ کد شما دریافت شد و در حال بررسی است.")
        return VERIFY_CODE
    
    except Exception as e:
        logger.error(f"خطا در ثبت کد تأیید: {str(e)}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
        return VERIFY_CODE

async def order_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت شماره سفارش کاربر"""
    try:
        user_id = str(update.effective_user.id)
        order_number = update.message.text
        
        data = load_data()
        user_data = data["users"].get(user_id, {})
        
        if user_data.get("status") != "pending_order":
            await update.message.reply_text("⚠️ درخواست نامعتبر. لطفاً مراحل را به ترتیب طی کنید.")
            return ORDER_CODE
            
        admin_text = (
            f"📦 درخواست فعال‌سازی حساب کاربر\n\n"
            f"👤 کاربر: {user_data.get('name', 'نامشخص')}\n"
            f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
            f"🆔 آیدی: {user_id}\n"
            f"🔢 شماره سفارش: {order_number}"
        )
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text
        )
        
        group_message = await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_text
        )
        
        data["pending_approvals"][str(admin_message.message_id)] = {
            "type": "order",
            "user_id": user_id
        }
        
        data["admin_messages"][str(admin_message.message_id)] = {
            "group_message_id": group_message.message_id,
            "user_id": user_id,
            "type": "order"
        }
        
        save_data(data)
        
        await update.message.reply_text(
            "✅ شماره سفارش شما دریافت شد و در حال بررسی است.\n\n"
            "پس از تأیید ادمین، حساب شما فعال خواهد شد."
        )
        return ORDER_CODE
    
    except Exception as e:
        logger.error(f"خطا در ثبت شماره سفارش: {str(e)}")
        await update.message.reply_text("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
        return ORDER_CODE

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت پاسخ‌های ادمین"""
    if update.effective_chat.id != ADMIN_ID:
        return
    
    if not update.message.reply_to_message:
        return
    
    # Handle admin commands
    text = update.message.text.strip().lower()
    
    # Check for admin commands
    if text.startswith('/edit'):
        await handle_admin_edit_command(update, context)
        return
    elif text.startswith('/delete'):
        await handle_admin_delete_command(update, context)
        return
    elif text.startswith('/deactive'):
        await handle_admin_deactive_command(update, context)
        return
    elif text.startswith('/reactive'):
        await handle_admin_reactive_command(update, context)
        return
    
    if not update.message.reply_to_message.from_user.is_bot:
        return
    
    data = load_data()
    replied_message_id = str(update.message.reply_to_message.message_id)
    
    if replied_message_id not in data["pending_approvals"]:
        return
    
    approval_data = data["pending_approvals"][replied_message_id]
    request_type = approval_data["type"]
    user_id = approval_data["user_id"]
    
    if user_id not in data["users"]:
        await update.message.reply_text("⚠️ کاربر مورد نظر یافت نشد!")
        return
    
    user_data = data["users"][user_id]
    
    if request_type == "registration":
        if text == "1":
            user_data["status"] = "pending_verification"
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ ثبت‌نام شما تأیید شد.\n\n"
                     "لطفاً کد تأیید ارسال شده به شماره همراه خود را وارد کنید:"
            )
            await update.message.reply_text(f"✅ ثبت‌نام کاربر {user_data['name']} تأیید شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"✅ ثبت‌نام کاربر {user_data['name']} تأیید شد.\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
        elif text == "0":
            user_data["status"] = "rejected"
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ ثبت‌نام شما رد شد. برای پیگیری به {SUPPORT_USERNAME} پیام دهید."
            )
            await update.message.reply_text(f"❌ ثبت‌نام کاربر {user_data['name']} رد شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"❌ ثبت‌نام کاربر {user_data['name']} رد شد.\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
    
    elif request_type == "verification":
        if text == "1":
            user_data["status"] = "pending_order"
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 تایید هویت شما با موفقیت انجام شد.\n\n"
                    "برای فعال‌سازی حساب، کافیست حداقل 3 میلیون تومان یا بیشتر از محصولات برند لایمن یا مالیمن در فروشگاه آنلاین خرید و شماره سفارشتان را اینجا ارسال کنید.\n\n"
                    f"🛍️ آدرس فروشگاه: {SHOP_URL}\n\n"
                    "پس از خرید، لطفاً شماره سفارش خود را اینجا وارد کنید:"
                )
            )
            await update.message.reply_text(f"✅ کد تأیید کاربر {user_data['name']} تأیید شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"✅ کد تأیید کاربر {user_data['name']} تأیید شد.\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
        elif text == "0":
            user_data["status"] = "pending_verification"
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ کد تأیید نامعتبر است. لطفاً مجدداً کد تأیید را وارد کنید:"
            )
            await update.message.reply_text(f"❌ کد تأیید کاربر {user_data['name']} رد شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"❌ کد تأیید کاربر {user_data['name']} رد شد.\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
    
    elif request_type == "order":
        if text == "1":
            user_data["status"] = "active"
            user_data["activation_date"] = str(datetime.now())
            
            referrer_id = None
            for ref_id, ref_list in data["referrals"].items():
                if user_id in ref_list:
                    referrer_id = ref_id
                    break
            
            if referrer_id and referrer_id in data["users"]:
                referrer = data["users"][referrer_id]
                ref_count = len(data["referrals"].get(referrer_id, []))
                
                if ref_count % 2 == 0:
                    referrer["balance"] = referrer.get("balance", 0) + COMMISSION_RATE
                    
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 شما یک پورسانت جدید دریافت کردید.\n\n"
                             f"💰 مبلغ پورسانت: {COMMISSION_RATE:,} تومان\n"
                             f"👥 کاربران معرفی شده: {data['referrals'][referrer_id][-2:]}\n\n"
                             f"💵 موجودی کل شما: {referrer.get('balance', 0):,} تومان"
                    )
            
            # Notify referrer about new active referral
            if referrer_id:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 تبریک! زیرمجموعه جدید شما با موفقیت فعال شد:\n\n"
                         f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
                         f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n\n"
                         f"💰 ارزش فعال‌سازی: {REFERRAL_PURCHASE_VALUE:,} تومان به حساب شما اضافه شد."
                )
                
                # ثبت خرید فعالسازی برای کاربر معرف
                if "commissions" not in referrer:
                    referrer["commissions"] = []
                
                referrer["commissions"].append({
                    "type": "referral_activation",
                    "amount": REFERRAL_PURCHASE_VALUE,
                    "date": str(datetime.now()),
                    "user_id": user_id
                })
                
                # Remove from pending invites if exists
                if referrer_id in data["pending_invites"] and user_data.get("phone") in data["pending_invites"][referrer_id]:
                    data["pending_invites"][referrer_id].remove(user_data.get("phone"))
                    save_data(data)
            
            await show_main_menu(user_id, context, first_time=True)
            await update.message.reply_text(f"✅ سفارش کاربر {user_data['name']} تأیید شد. حساب کاربر فعال شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"✅ سفارش کاربر {user_data['name']} تأیید شد. حساب کاربر فعال شد.\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
            
            # Send confirmation to admin group
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"خرید جدید کاربر {user_data['name']} تائید شد."
            )
            
        elif text == "0":
            user_data["status"] = "order_rejected"
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ شماره سفارش نامعتبر است. لطفاً با پشتیبانی تماس بگیرید."
            )
            await update.message.reply_text(f"❌ سفارش کاربر {user_data['name']} رد شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"❌ سفارش کاربر {user_data['name']} رد شد.\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
    
    elif request_type == "withdrawal":
        amount = approval_data["amount"]
        if text != "0":
            user_data["balance"] = 0
            user_data["commissions_received"] = 0  # Reset commissions received after withdrawal
            
            if "withdrawals" not in user_data:
                user_data["withdrawals"] = []
            user_data["withdrawals"].append({
                "amount": amount,
                "date": str(datetime.now()),
                "status": "approved",
                "tracking_code": text
            })
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎉 تبریک! درخواست برداشت شما تأیید شد.\n\n"
                     f"💰 مبلغ برداشت: {amount:,} تومان\n"
                     f"🔢 کد پیگیری: {text}\n\n"
                     "مبلغ به کارت بانکی شما واریز شد."
            )
            await show_main_menu(user_id, context, first_time=False)
            await update.message.reply_text(f"✅ برداشت کاربر {user_data['name']} تأیید شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"✅ برداشت کاربر {user_data['name']} تأیید شد.\n"
                     f"💰 مبلغ: {amount:,} تومان\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
        elif text == "0":
            if "withdrawals" not in user_data:
                user_data["withdrawals"] = []
            user_data["withdrawals"].append({
                "amount": amount,
                "date": str(datetime.now()),
                "status": "rejected"
            })
            
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ درخواست برداشت شما رد شد. لطفاً با پشتیبانی تماس بگیرید."
            )
            await update.message.reply_text(f"❌ برداشت کاربر {user_data['name']} رد شد.")
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"❌ برداشت کاربر {user_data['name']} رد شد.\n"
                     f"💰 مبلغ: {amount:,} تومان\n"
                     f"🆔 آیدی کاربر: {user_id}"
            )
    
    elif request_type == "edit_address":
        if text == "1":
            user_data["address"] = approval_data["new_address"]
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ آدرس شما با موفقیت به روزرسانی شد."
            )
            await update.message.reply_text(f"✅ آدرس کاربر {user_data['name']} به روزرسانی شد.")
        elif text == "0":
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ درخواست تغییر آدرس شما رد شد."
            )
            await update.message.reply_text(f"❌ تغییر آدرس کاربر {user_data['name']} رد شد.")
    
    elif request_type == "edit_postal_code":
        if text == "1":
            user_data["postal_code"] = approval_data["new_postal_code"]
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ کد پستی شما با موفقیت به روزرسانی شد."
            )
            await update.message.reply_text(f"✅ کد پستی کاربر {user_data['name']} به روزرسانی شد.")
        elif text == "0":
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ درخواست تغییر کد پستی شما رد شد."
            )
            await update.message.reply_text(f"❌ تغییر کد پستی کاربر {user_data['name']} رد شد.")
    
    elif request_type == "bank_card":
        if text == "1":
            user_data["bank_card"] = approval_data["new_card"]
            user_data["bank_card_verified"] = True
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ شماره کارت شما با موفقیت تأیید شد."
            )
            await show_main_menu(user_id, context, first_time=False)
            await update.message.reply_text(f"✅ شماره کارت کاربر {user_data['name']} تأیید شد.")
        elif text == "0":
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ درخواست تغییر شماره کارت شما رد شد."
            )
            await update.message.reply_text(f"❌ تغییر شماره کارت کاربر {user_data['name']} رد شد.")
    
    elif request_type == "complete_commission":
        try:
            if text == "0":
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ درخواست خرید جدید شما رد شد."
                )
                await update.message.reply_text(f"❌ خرید جدید کاربر {user_data['name']} رد شد.")
            else:
                purchase_amount = float(text)
                amount = int(purchase_amount * 1000000)
                
                # Calculate commissions from all purchases (user + referrals)
                total_purchases = 0
                
                # Add user's own purchases
                user_purchases = [p for p in user_data.get("commissions", []) if p["type"] == "complete"]
                total_purchases += sum(p['amount'] for p in user_purchases)
                
                # Add referral purchases
                referrals = data["referrals"].get(user_id, [])
                for ref_id in referrals:
                    ref_data = data["users"].get(ref_id, {})
                    # Add activation value if active
                    if ref_data.get("status") == "active":
                        total_purchases += REFERRAL_PURCHASE_VALUE
                    # Add referral purchases
                    for purchase in ref_data.get("commissions", []):
                        if purchase["type"] == "complete":
                            total_purchases += purchase["amount"]
                
                # Add the new purchase
                total_purchases += amount
                
                # Calculate commissions
                commissions_to_add = total_purchases // COMMISSION_THRESHOLD
                pending_purchases = total_purchases % COMMISSION_THRESHOLD
                
                # Update user balance
                user_data["balance"] = commissions_to_add * COMMISSION_RATE
                
                # Save the new purchase
                if "commissions" not in user_data:
                    user_data["commissions"] = []
                
                user_data["commissions"].append({
                    "type": "complete",
                    "amount": amount,
                    "date": str(datetime.now()),
                    "order_number": approval_data["order_number"],
                    "status": "calculated" if pending_purchases == 0 else "pending"
                })
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ خرید جدید شما به مبلغ {amount:,} تومان ثبت شد.\n\n"
                         f"💰 موجودی قابل برداشت شما: {user_data.get('balance', 0):,} تومان\n"
                         f"🛒 خرید در صف پورسانت: {pending_purchases:,} تومان"
                )
                await update.message.reply_text(f"✅ خرید جدید کاربر {user_data['name']} ثبت شد.")
                
                # ثبت خرید برای کاربر معرف
                referrer_id = None
                for ref_id, ref_list in data["referrals"].items():
                    if user_id in ref_list:
                        referrer_id = ref_id
                        break
                
                if referrer_id and referrer_id in data["users"]:
                    referrer = data["users"][referrer_id]
                    
                    if "commissions" not in referrer:
                        referrer["commissions"] = []
                    
                    referrer["commissions"].append({
                        "type": "referral_purchase",
                        "amount": amount,
                        "date": str(datetime.now()),
                        "user_id": user_id
                    })
                    save_data(data)
                
                # Send confirmation to admin group with details
                await context.bot.send_message(
                    chat_id=ADMIN_GROUP_ID,
                    text=f"خرید جدید کاربر {user_data['name']} تائید شد.\n"
                         f"🔢 شماره سفارش: {approval_data['order_number']}\n"
                         f"💰 مبلغ تائید شده: {amount:,} تومان\n"
                         f"📌 مربوط به درخواست خرید: {approval_data['order_number']}"
                )
                
        except ValueError:
            await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید.")
            return
    
    del data["pending_approvals"][replied_message_id]
    save_data(data)

async def handle_admin_edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت دستورات ویرایش ادمین"""
    try:
        parts = update.message.text.strip().split()
        if len(parts) < 3:
            await update.message.reply_text("⚠️ فرمت دستور نادرست است. مثال: /edit user_id field new_value")
            return
        
        user_id = parts[1]
        field = parts[2]
        new_value = ' '.join(parts[3:]) if len(parts) > 3 else ""
        
        data = load_data()
        
        if user_id not in data["users"]:
            await update.message.reply_text("⚠️ کاربر مورد نظر یافت نشد.")
            return
        
        if field not in data["users"][user_id]:
            await update.message.reply_text("⚠️ فیلد مورد نظر یافت نشد.")
            return
        
        old_value = data["users"][user_id][field]
        data["users"][user_id][field] = new_value
        save_data(data)
        
        await update.message.reply_text(
            f"✅ اطلاعات کاربر با موفقیت به روز شد.\n\n"
            f"🆔 آیدی کاربر: {user_id}\n"
            f"📌 فیلد: {field}\n"
            f"🔹 مقدار قدیمی: {old_value}\n"
            f"🔸 مقدار جدید: {new_value}"
        )
        
        # ارسال پیام به گروه ادمین برای آرشیو
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"📝 ادمین اطلاعات کاربر را ویرایش کرد:\n\n"
                 f"👤 کاربر: {data['users'][user_id].get('name', 'نامشخص')}\n"
                 f"🆔 آیدی: {user_id}\n"
                 f"📌 فیلد: {field}\n"
                 f"🔹 مقدار قدیمی: {old_value}\n"
                 f"🔸 مقدار جدید: {new_value}"
        )
    except Exception as e:
        logger.error(f"Error in handle_admin_edit_command: {str(e)}")
        await update.message.reply_text("⚠️ خطایی در پردازش دستور رخ داد.")

async def handle_admin_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت دستورات حذف ادمین"""
    try:
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("⚠️ فرمت دستور نادرست است. مثال: /delete user_id")
            return
        
        user_id = parts[1]
        data = load_data()
        
        if user_id not in data["users"]:
            await update.message.reply_text("⚠️ کاربر مورد نظر یافت نشد.")
            return
        
        user_data = data["users"].pop(user_id)
        
        # Remove from referrals
        for ref_id, ref_list in data["referrals"].items():
            if user_id in ref_list:
                data["referrals"][ref_id].remove(user_id)
        
        save_data(data)
        
        await update.message.reply_text(
            f"✅ کاربر با موفقیت حذف شد.\n\n"
            f"🆔 آیدی کاربر: {user_id}\n"
            f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
            f"📞 شماره: {user_data.get('phone', 'نامشخص')}"
        )
        
        # ارسال پیام به گروه ادمین برای آرشیو
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"❌ ادمین کاربر را حذف کرد:\n\n"
                 f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
                 f"🆔 آیدی: {user_id}\n"
                 f"📞 شماره: {user_data.get('phone', 'نامشخص')}"
        )
    except Exception as e:
        logger.error(f"Error in handle_admin_delete_command: {str(e)}")
        await update.message.reply_text("⚠️ خطایی در پردازش دستور رخ داد.")

async def handle_admin_deactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت دستورات غیرفعال کردن ادمین"""
    try:
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("⚠️ فرمت دستور نادرست است. مثال: /deactive user_id")
            return
        
        user_id = parts[1]
        data = load_data()
        
        if user_id not in data["users"]:
            await update.message.reply_text("⚠️ کاربر مورد نظر یافت نشد.")
            return
        
        old_status = data["users"][user_id]["status"]
        data["users"][user_id]["status"] = "inactive"
        save_data(data)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ حساب شما توسط ادمین غیرفعال شده است. لطفاً با پشتیبانی تماس بگیرید."
        )
        
        await update.message.reply_text(
            f"✅ حساب کاربر با موفقیت غیرفعال شد.\n\n"
            f"🆔 آیدی کاربر: {user_id}\n"
            f"👤 نام: {data['users'][user_id].get('name', 'نامشخص')}\n"
            f"🔘 وضعیت قبلی: {old_status}\n"
            f"🔘 وضعیت جدید: inactive"
        )
        
        # ارسال پیام به گروه ادمین برای آرشیو
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"⚠️ ادمین کاربر را غیرفعال کرد:\n\n"
                 f"👤 نام: {data['users'][user_id].get('name', 'نامشخص')}\n"
                 f"🆔 آیدی: {user_id}\n"
                 f"📞 شماره: {data['users'][user_id].get('phone', 'نامشخص')}\n"
                 f"🔘 وضعیت قبلی: {old_status}"
        )
    except Exception as e:
        logger.error(f"Error in handle_admin_deactive_command: {str(e)}")
        await update.message.reply_text("⚠️ خطایی در پردازش دستور رخ داد.")

async def handle_admin_reactive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت دستورات فعال کردن مجدد ادمین"""
    try:
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("⚠️ فرمت دستور نادرست است. مثال: /reactive user_id")
            return
        
        user_id = parts[1]
        data = load_data()
        
        if user_id not in data["users"]:
            await update.message.reply_text("⚠️ کاربر مورد نظر یافت نشد.")
            return
        
        old_status = data["users"][user_id]["status"]
        data["users"][user_id]["status"] = "active"
        save_data(data)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ حساب شما توسط ادمین مجدداً فعال شد."
        )
        
        await update.message.reply_text(
            f"✅ حساب کاربر با موفقیت فعال شد.\n\n"
            f"🆔 آیدی کاربر: {user_id}\n"
            f"👤 نام: {data['users'][user_id].get('name', 'نامشخص')}\n"
            f"🔘 وضعیت قبلی: {old_status}\n"
            f"🔘 وضعیت جدید: active"
        )
        
        # ارسال پیام به گروه ادمین برای آرشیو
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"✅ ادمین کاربر را مجدداً فعال کرد:\n\n"
                 f"👤 نام: {data['users'][user_id].get('name', 'نامشخص')}\n"
                 f"🆔 آیدی: {user_id}\n"
                 f"📞 شماره: {data['users'][user_id].get('phone', 'نامشخص')}\n"
                 f"🔘 وضعیت قبلی: {old_status}"
        )
    except Exception as e:
        logger.error(f"Error in handle_admin_reactive_command: {str(e)}")
        await update.message.reply_text("⚠️ خطایی در پردازش دستور رخ داد.")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش راهنمای ربات"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = (
        "📚 راهنمای ربات کسب درآمد لایمن:\n\n"
        "🌟 سلام دوست عزیز! این ربات به شما کمک می‌کند تا از طریق همکاری در فروش محصولات لایمن درآمد داشته باشید.\n\n"
        "💡 نحوه کار ربات:\n"
        "1. ثبت شماره سفارش: با هر خرید شما از فروشگاه و ثبت شماره سفارش در ربات، پورسانت خرید به شما تعلق می‌گیرد\n"
        "2. معرفی دوستان: با معرفی دوستان خود، از خریدهای آن‌ها هم سود می‌برید (9% مبلغ خرید هر دو زیرمجموعه به شما تعلق می‌گیرد)\n"
        f"3. دریافت پورسانت: به ازای هر 6 میلیون تومان خرید (شما و دوستانتان) {COMMISSION_RATE:,} تومان پورسانت دریافت می‌کنید\n\n"
        "ℹ️ نکات مهم در معرفی دوستان:\n"
        "• کاربر معرفی شده حتماً باید از لینک دعوت اختصاصی شما ثبت نام کند\n"
        "• پس از ثبت نام و فعال شدن حساب کاربر معرفی شده، به عنوان زیرمجموعه شما محسوب می‌شود\n"
        "• خریدهای کاربران معرفی شده پس از فعال شدن حسابشان، در پورسانت شما محاسبه می‌شود\n\n"
        "📌 نکات مهم:\n"
        "• فقط خرید محصولات ارگانیک برند لایمن یا مالیمن محاسبه می‌شود\n"
        "• برای برداشت پورسانت باید شماره کارت بانکی خود را ثبت کنید\n"
        f"• می‌توانید هر زمان که موجودی شما به {COMMISSION_RATE:,} تومان رسید، درخواست برداشت دهید"
    )
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    await track_message(str(query.from_user.id), "help", query.message.message_id)

async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت معرفی دوستان"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔗 دریافت لینک دعوت", callback_data="get_invite_link")],
        [InlineKeyboardButton("📈 زیرمجموعه‌ها", callback_data="subsets")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👥 معرفی دوستان:\n\n"
        "می‌توانید دوستان خود را از طریق لینک دعوت اختصاصی به عنوان زیرمجموعه خود معرفی کنید.\n\n"
        "✨ مزایای معرفی دوستان:\n"
        f"• با هر دو نفری که معرفی می‌کنید و حسابشان فعال می‌شود، مبلغ {COMMISSION_RATE:,} تومان پورسانت دریافت خواهید کرد.\n"
        f"• با فعال شدن حساب زیرمجموعه‌ها به صورت مادام‌العمر، از هر خرید آنها کسب درآمد مستقیم دارید.\n"
        f"• درآمد شما به راحتی از ربات قابل برداشت و انتقال به حساب بانکی شماست.",
        reply_markup=reply_markup
    )
    await track_message(user_id, "invite_friends", query.message.message_id)

async def get_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت لینک دعوت اختصاصی"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📱 ارسال شماره همراه زیرمجموعه جدید", callback_data="get_friends_phones")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    invite_link = f"https://t.me/limen_income_bot?start={user_id}"
    
    await query.edit_message_text(
        "🔗 لینک دعوت اختصاصی شما:\n\n"
        f"{invite_link}\n\n"
        "لطفاً شماره همراه دوست خود را وارد کنید تا پس از فعال شدن حسابش به عنوان زیر مجموعه شما قرار گیرد و پیام دعوت دریافتی را برای او ارسال کنید.",
        reply_markup=reply_markup
    )

async def get_friends_phones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت شماره تلفن دوستان معرفی شده"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📱 لطفاً شماره همراه زیرمجموعه جدید را وارد کنید (مثال: 09123456789):",
        reply_markup=reply_markup
    )
    return INVITE_1

async def invite_1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت شماره تلفن دوست اول"""
    user_id = str(update.effective_user.id)
    phone = normalize_phone(update.message.text)
    
    if len(phone) != 11:
        await update.message.reply_text("❌ شماره موبایل باید 11 رقم باشد! لطفاً مجدداً وارد کنید:")
        return INVITE_1
    
    data = load_data()
    
    for uid, u_data in data["users"].items():
        if u_data.get("phone") == phone:
            await update.message.reply_text("⚠️ این شماره موبایل قبلاً ثبت‌نام کرده است.")
            
            # Send invite link again even if number was already invited
            invite_link = f"https://t.me/limen_income_bot?start={user_id}"
            await update.message.reply_text(
                f"سلام دوست عزیز،\n\n"
                f"من از پلن درآمدی لایمن استفاده می‌کنم و می‌خواهم شما هم در این درآمد شگفت‌انگیز شریک باشید.\n\n"
                f"💵 با هر دو نفری که معرفی کنید، {COMMISSION_RATE:,} تومان پورسانت دریافت می‌کنید.\n\n"
                f"🔗 لینک دعوت اختصاصی من:\n{invite_link}"
            )
            
            await show_main_menu(user_id, context, first_time=False)
            return ConversationHandler.END
    
    user_data = data["users"].get(user_id, {})
    
    if "pending_invites" not in data:
        data["pending_invites"] = {}
    
    if user_id not in data["pending_invites"]:
        data["pending_invites"][user_id] = []
    
    if phone in data["pending_invites"][user_id]:
        await update.message.reply_text("⚠️ این شماره موبایل قبلاً توسط شما دعوت شده است.")
        
        # Send invite link again even if number was already invited
        invite_link = f"https://t.me/limen_income_bot?start={user_id}"
        await update.message.reply_text(
            f"سلام دوست عزیز،\n\n"
            f"من از پلن درآمدی لایمن استفاده می‌کنم و می‌خواهم شما هم در این درآمد شگفت‌انگیز شریک باشید.\n\n"
            f"💵 با هر دو نفری که معرفی کنید، {COMMISSION_RATE:,} تومان پورسانت دریافت می‌کنید.\n\n"
            f"🔗 لینک دعوت اختصاصی من:\n{invite_link}"
        )
        
        await show_main_menu(user_id, context, first_time=False)
        return ConversationHandler.END
    
    data["pending_invites"][user_id].append(phone)
    save_data(data)
    
    invite_link = f"https://t.me/limen_income_bot?start={user_id}"
    
    await update.message.reply_text(
        "✅ شماره همراه زیرمجموعه جدید ثبت شد.\n\n"
        "لطفاً پیام دعوت زیر را برای دوست خود ارسال کنید:"
    )
    
    await update.message.reply_text(
        f"سلام دوست عزیز،\n\n"
        f"من از پلن درآمدی لایمن استفاده می‌کنم و می‌خواهم شما هم در این درآمد شگفت‌انگیز شریک باشید.\n\n"
        f"💵 با هر دو نفری که معرفی کنید، {COMMISSION_RATE:,} تومان پورسانت دریافت می‌کنید.\n\n"
        f"🔗 لینک دعوت اختصاصی من:\n{invite_link}"
    )
    
    await show_main_menu(user_id, context, first_time=False)
    return ConversationHandler.END

async def bank_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """مدیریت ثبت و تغییر شماره کارت بانکی"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = str(update.effective_user.id)
    
    if query:
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "💳 لطفاً شماره کارت بانکی 16 رقمی خود را وارد کنید (شماره کارت حتماً به نام خود کاربر باشد):",
            reply_markup=reply_markup
        )
        return BANK_CARD
    
    card_number = normalize_number(update.message.text)
    
    if len(card_number) != 16 or not card_number.isdigit():
        await update.message.reply_text("❌ شماره کارت نامعتبر! لطفاً یک شماره کارت 16 رقمی وارد کنید:")
        return BANK_CARD
    
    data = load_data()
    user_data = data["users"].get(user_id, {})
    user_data["bank_card"] = card_number
    
    admin_text = (
        f"💳 درخواست ثبت شماره کارت جدید\n\n"
        f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
        f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
        f"🆔 آیدی: {user_id}\n"
        f"💳 شماره کارت: {card_number}"
    )
    
    admin_message = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text
    )
    
    group_message = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_text
    )
    
    data["pending_approvals"][str(admin_message.message_id)] = {
        "type": "bank_card",
        "user_id": user_id,
        "new_card": card_number
    }
    
    data["admin_messages"][str(admin_message.message_id)] = {
        "group_message_id": group_message.message_id,
        "user_id": user_id,
        "type": "bank_card"
    }
    
    save_data(data)
    
    await update.message.reply_text(
        "✅ شماره کارت شما دریافت شد و برای تأیید به ادمین ارسال شد.\n\n"
        "پس از تأیید ادمین، شماره کارت شما فعال خواهد شد."
    )
    await show_main_menu(user_id, context, first_time=False)
    return ConversationHandler.END

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش پروفایل کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    status_persian = {
        "active": "فعال",
        "pending_registration": "در انتظار تایید ثبت‌نام",
        "pending_verification": "در انتظار تایید کد",
        "pending_order": "در انتظار تایید سفارش",
        "rejected": "رد شده",
        "verification_failed": "کد تایید نامعتبر",
        "order_rejected": "سفارش رد شده",
        "inactive": "غیرفعال"
    }
    
    text = (
        f"📊 پروفایل شما:\n\n"
        f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
        f"📞 شماره همراه: {user_data.get('phone', 'نامشخص')}\n"
        f"🏠 آدرس: {user_data.get('address', 'نامشخص')}\n"
        f"📮 کد پستی: {user_data.get('postal_code', 'نامشخص')}\n"
        f"💳 شماره کارت: {user_data.get('bank_card', 'ثبت نشده')}\n"
        f"🔘 وضعیت حساب: {status_persian.get(user_data.get('status', 'نامشخص'))}\n\n"
        f"💰 موجودی قابل برداشت: {user_data.get('balance', 0):,} تومان"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ ویرایش آدرس", callback_data="edit_address")],
        [InlineKeyboardButton("✏️ ویرایش کد پستی", callback_data="edit_postal_code")],
        [InlineKeyboardButton("✏️ ویرایش شماره کارت", callback_data="bank_card")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    await track_message(user_id, "profile", query.message.message_id)

async def edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند ویرایش آدرس"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏠 ویرایش آدرس:\n\n"
        f"آدرس فعلی: {user_data.get('address', 'نامشخص')}\n\n"
        "لطفاً آدرس جدید خود را وارد کنید:",
        reply_markup=reply_markup
    )
    return EDIT_ADDRESS

async def save_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ذخیره آدرس جدید کاربر"""
    user_id = str(update.effective_user.id)
    new_address = update.message.text
    
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    admin_text = (
        f"📝 درخواست تغییر آدرس کاربر\n\n"
        f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
        f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
        f"🆔 آیدی: {user_id}\n\n"
        f"🏠 آدرس جدید:\n{new_address}"
    )
    
    admin_message = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text
    )
    
    group_message = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_text
    )
    
    data["pending_approvals"][str(admin_message.message_id)] = {
        "type": "edit_address",
        "user_id": user_id,
        "new_address": new_address
    }
    
    data["admin_messages"][str(admin_message.message_id)] = {
        "group_message_id": group_message.message_id,
        "user_id": user_id,
        "type": "edit_address"
    }
    
    save_data(data)
    
    await update.message.reply_text(
        "✅ درخواست تغییر آدرس شما برای تائید به ادمین ارسال شد.\n"
        "پس از تائید، آدرس شما به روزرسانی خواهد شد."
    )
    await show_main_menu(user_id, context, first_time=False)
    return ConversationHandler.END

async def edit_postal_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند ویرایش کد پستی"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📮 ویرایش کد پستی:\n\n"
        f"کد پستی فعلی: {user_data.get('postal_code', 'نامشخص')}\n\n"
        "لطفاً کد پستی جدید خود را وارد کنید:",
        reply_markup=reply_markup
    )
    return EDIT_POSTAL_CODE

async def save_edit_postal_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ذخیره کد پستی جدید کاربر"""
    user_id = str(update.effective_user.id)
    new_postal_code = normalize_number(update.message.text)
    
    if len(new_postal_code) != 10:
        await update.message.reply_text("❌ کد پستی باید 10 رقم باشد! لطفاً مجدداً وارد کنید:")
        return EDIT_POSTAL_CODE
    
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    admin_text = (
        f"📝 درخواست تغییر کد پستی کاربر\n\n"
        f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
        f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
        f"🆔 آیدی: {user_id}\n\n"
        f"📮 کد پستی جدید: {new_postal_code}"
    )
    
    admin_message = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text
    )
    
    group_message = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_text
    )
    
    data["pending_approvals"][str(admin_message.message_id)] = {
        "type": "edit_postal_code",
        "user_id": user_id,
        "new_postal_code": new_postal_code
    }
    
    data["admin_messages"][str(admin_message.message_id)] = {
        "group_message_id": group_message.message_id,
        "user_id": user_id,
        "type": "edit_postal_code"
    }
    
    save_data(data)
    
    await update.message.reply_text(
        "✅ درخواست تغییر کد پستی شما برای تائید به ادمین ارسال شد.\n"
        "پس از تائید، کد پستی شما به روزرسانی خواهد شد."
    )
    await show_main_menu(user_id, context, first_time=False)
    return ConversationHandler.END

async def subsets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش زیرمجموعه‌های کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    referrals = data["referrals"].get(user_id, [])
    active_refs = [ref_id for ref_id in referrals if data["users"].get(ref_id, {}).get("status") == "active"]
    pending_invites = data["pending_invites"].get(user_id, [])
    
    # محاسبه کل خریدهای فعالسازی
    total_activation_value = len(active_refs) * REFERRAL_PURCHASE_VALUE
    
    # محاسبه کل خریدهای زیرمجموعه‌ها
    referral_purchases = 0
    for ref_id in active_refs:
        ref_data = data["users"].get(ref_id, {})
        for purchase in ref_data.get("commissions", []):
            if purchase["type"] == "complete":
                referral_purchases += purchase["amount"]
    
    # محاسبه کل مبلغ خریدها
    total_purchases = total_activation_value + referral_purchases
    
    # محاسبه پورسانت‌های قابل دریافت (همان مقدار موجود در بخش پورسانت‌ها)
    commissions_available = user_data.get("balance", 0) // COMMISSION_RATE
    
    text = (
        f"📈 زیرمجموعه‌های شما:\n\n"
        f"👥 تعداد کل زیرمجموعه‌های معرفی شده: {len(active_refs) + len(pending_invites)}\n"
        f"✅ زیرمجموعه‌های فعال: {len(active_refs)}\n"
        f"📱 کاربران فعال:\n"
    )
    
    for ref_id in active_refs[-5:]:
        ref_data = data["users"].get(ref_id, {})
        text += f"- {ref_data.get('name', 'نامشخص')} ({ref_data.get('phone', 'نامشخص')})\n"
    
    text += f"\n❌ زیرمجموعه‌های غیرفعال: {len(pending_invites)}\n"
    text += f"📱 کاربران غیرفعال:\n"
    
    for phone in pending_invites[-5:]:
        text += f"- {phone}\n"
    
    text += (
        f"\n💰 خرید فعالسازی زیرمجموعه‌ها: {total_activation_value:,} تومان\n"
        f"🛒 خریدهای زیرمجموعه‌ها: {referral_purchases:,} تومان\n"
        f"\n🎯 تعداد پورسانت قابل دریافت: {commissions_available}"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن زیرمجموعه", callback_data="get_invite_link")],
        [InlineKeyboardButton("💰 پورسانت‌ها", callback_data="my_commissions")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    await track_message(user_id, "subsets", query.message.message_id)

async def my_commissions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش پورسانت‌های کاربر"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    # محاسبه کل خریدهای کاربر و زیرمجموعه‌ها
    total_purchases = 0
    
    # محاسبه خریدهای کاربر (از قدیم به جدید)
    user_purchases = [p for p in user_data.get("commissions", []) if p["type"] == "complete"]
    total_user_purchases = sum(p['amount'] for p in user_purchases)
    
    # محاسبه خریدهای زیرمجموعه‌ها (از قدیم به جدید)
    referral_purchases = []
    referrals = data["referrals"].get(user_id, [])
    for ref_id in referrals:
        ref_data = data["users"].get(ref_id, {})
        # افزودن خریدهای فعالسازی
        if ref_data.get("status") == "active":
            referral_purchases.append({
                "type": "referral_activation",
                "amount": REFERRAL_PURCHASE_VALUE,
                "date": ref_data.get("activation_date", ""),
                "user_id": ref_id,
                "user_name": ref_data.get("name", "نامشخص"),
                "status": "calculated"
            })
        # افزودن خریدهای واقعی زیرمجموعه
        for purchase in ref_data.get("commissions", []):
            if purchase["type"] == "complete":
                referral_purchases.append({
                    "type": "referral_purchase",
                    "amount": purchase["amount"],
                    "date": purchase.get("date", ""),
                    "user_id": ref_id,
                    "user_name": ref_data.get("name", "نامشخص"),
                    "status": "calculated" if purchase.get("status") == "calculated" else "pending"
                })
    
    # ترکیب تمام خریدها (کاربر + زیرمجموعه‌ها) به ترتیب تاریخ
    all_purchases = sorted(
        user_purchases + referral_purchases,
        key=lambda x: x.get("date", "1970-01-01")
    )
    
    # محاسبه کل مبلغ خریدها
    total_purchases = sum(p['amount'] for p in all_purchases)
    
    # محاسبه پورسانت‌های قابل دریافت
    commissions_available = total_purchases // COMMISSION_THRESHOLD
    
    # محاسبه خریدهای در صف پورسانت
    pending_purchases = total_purchases % COMMISSION_THRESHOLD
    
    # محاسبه مبلغ مورد نیاز برای پورسانت بعدی
    remaining_for_commission = COMMISSION_THRESHOLD - pending_purchases if pending_purchases > 0 else 0
    
    text = (
        f"💰 پورسانت‌های شما:\n\n"
        f"✨ هر 6 میلیون تومان خرید (شما و زیرمجموعه‌ها) معادل یک پورسانت {COMMISSION_RATE:,} تومانی است.\n\n"
        f"🎯 پورسانت‌های قابل دریافت: {commissions_available}\n\n"
    )
    
    # نمایش خریدهای کاربر (از قدیم به جدید)
    text += f"🛒 خریدهای شما:\n"
    if pending_purchases == 0:
        # اگر خرید در صف پورسانت صفر است، همه خریدها محاسبه شده هستند
        for purchase in user_purchases:
            text += f"- {purchase['amount']:,} تومان (محاسبه شده)\n"
    else:
        # در غیر این صورت، خریدهای جدیدتر که در صف هستند به صورت کامل محاسبه نشده نمایش داده می‌شوند
        for i, purchase in enumerate(user_purchases):
            if i < len(user_purchases) - (pending_purchases // COMMISSION_THRESHOLD + 1):
                status = "محاسبه شده"
            else:
                status = "کامل محاسبه نشده"
            text += f"- {purchase['amount']:,} تومان ({status})\n"
    
    # نمایش خریدهای زیرمجموعه‌ها (از قدیم به جدید)
    text += f"\n🛒 خریدهای زیرمجموعه‌ها:\n"
    if pending_purchases == 0:
        # اگر خرید در صف پورسانت صفر است، همه خریدها محاسبه شده هستند
        for purchase in referral_purchases:
            text += f"- {purchase['amount']:,} تومان (محاسبه شده) - {purchase['user_name']}"
            if purchase['type'] == 'referral_activation':
                text += " (فعالسازی حساب)"
            text += "\n"
    else:
        # در غیر این صورت، خریدهای جدیدتر که در صف هستند به صورت کامل محاسبه نشده نمایش داده می‌شوند
        for i, purchase in enumerate(referral_purchases):
            if i < len(referral_purchases) - (pending_purchases // COMMISSION_THRESHOLD + 1):
                status = "محاسبه شده"
            else:
                status = "کامل محاسبه نشده"
            text += f"- {purchase['amount']:,} تومان ({status}) - {purchase['user_name']}"
            if purchase['type'] == 'referral_activation':
                text += " (فعالسازی حساب)"
            text += "\n"
    
    text += (
        f"\n📊 خرید در صف پورسانت: {pending_purchases:,} تومان\n"
        f"💳 موجودی قابل برداشت: {commissions_available * COMMISSION_RATE:,} تومان\n\n"
    )
    
    if pending_purchases > 0:
        text += f"💡 هم اکنون می‌توانید با خرید {remaining_for_commission:,} تومان یک پورسانت جدید دریافت کنید.\n"
    
    keyboard = [
        [InlineKeyboardButton("🛒 ثبت شماره سفارش", callback_data="complete_commission")],
        [InlineKeyboardButton("💰 درخواست برداشت", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    await track_message(user_id, "my_commissions", query.message.message_id)

async def complete_commission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ثبت سفارش جدید برای دریافت پورسانت"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛒 ثبت شماره سفارش:\n\n"
        "🎉 از اعتماد و خرید شما متشکریم.\n\n"
        "⚠️ توجه: فقط خرید محصولات برند لایمن و مالیمن برای دریافت پورسانت محاسبه می‌شود.\n\n"
        "لطفاً شماره سفارش خود را وارد کنید:",
        reply_markup=reply_markup
    )
    return COMPLETE_COMMISSION

async def handle_complete_commission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پردازش سفارش جدید برای دریافت پورسانت"""
    user_id = str(update.effective_user.id)
    order_number = update.message.text
    
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    admin_text = (
        f"🛒 درخواست ثبت سفارش جدید\n\n"
        f"👤 کاربر: {user_data.get('name', 'نامشخص')}\n"
        f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
        f"🆔 آیدی: {user_id}\n"
        f"🔢 شماره سفارش: {order_number}"
    )
    
    admin_message = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text
    )
    
    group_message = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_text
    )
    
    data["pending_approvals"][str(admin_message.message_id)] = {
        "type": "complete_commission",
        "user_id": user_id,
        "order_number": order_number
    }
    
    data["admin_messages"][str(admin_message.message_id)] = {
        "group_message_id": group_message.message_id,
        "user_id": user_id,
        "type": "complete_commission"
    }
    
    save_data(data)
    
    await update.message.reply_text(
        "✅ شماره سفارش شما دریافت شد و برای تأیید به ادمین ارسال شد.\n\n"
        "پس از تأیید ادمین، مبلغ سفارش به حساب شما اضافه خواهد شد."
    )
    await show_main_menu(user_id, context, first_time=False)
    return ConversationHandler.END

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند برداشت پورسانت"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if user_data.get("status") != "active":
        await query.edit_message_text("⚠️ حساب شما فعال نیست. لطفاً مراحل فعال‌سازی را کامل کنید.")
        return
    
    if "bank_card" not in user_data or not user_data.get("bank_card_verified", False):
        await query.edit_message_text(
            "❌ ابتدا باید شماره کارت خود را ثبت و تأیید کنید.\n\n"
            "لطفاً از بخش پروفایل من، شماره کارت بانکی خود را ثبت کنید."
        )
        await show_main_menu(user_id, context, first_time=False)
        return
    
    # محاسبه کل خریدها برای تعیین پورسانت قابل دریافت
    total_purchases = 0
    
    # محاسبه خریدهای کاربر
    user_purchases = [p for p in user_data.get("commissions", []) if p["type"] == "complete"]
    total_purchases += sum(p['amount'] for p in user_purchases)
    
    # محاسبه خریدهای زیرمجموعه‌ها
    referrals = data["referrals"].get(user_id, [])
    for ref_id in referrals:
        ref_data = data["users"].get(ref_id, {})
        # افزودن خریدهای فعالسازی
        if ref_data.get("status") == "active":
            total_purchases += REFERRAL_PURCHASE_VALUE
        # افزودن خریدهای واقعی زیرمجموعه
        for purchase in ref_data.get("commissions", []):
            if purchase["type"] == "complete":
                total_purchases += purchase["amount"]
    
    # محاسبه پورسانت‌های قابل دریافت
    commissions_available = total_purchases // COMMISSION_THRESHOLD
    
    if commissions_available < 1:
        await query.edit_message_text(
            f"❌ موجودی قابل برداشت شما کافی نیست.\n\n"
            f"💰 پورسانت‌های قابل دریافت: {commissions_available}\n"
            f"💵 حداقل برداشت: 1 پورسانت ({COMMISSION_RATE:,} تومان)"
        )
        return
    
    withdraw_amount = commissions_available * COMMISSION_RATE
    
    admin_text = (
        f"💳 درخواست برداشت جدید\n\n"
        f"👤 نام: {user_data.get('name', 'نامشخص')}\n"
        f"📞 شماره: {user_data.get('phone', 'نامشخص')}\n"
        f"🆔 آیدی: {user_id}\n"
        f"💳 شماره کارت: {user_data['bank_card']}\n"
        f"💰 مبلغ درخواستی: {withdraw_amount:,} تومان"
    )
    
    admin_message = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text
    )
    
    group_message = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_text
    )
    
    data["pending_approvals"][str(admin_message.message_id)] = {
        "type": "withdrawal",
        "user_id": user_id,
        "amount": withdraw_amount
    }
    
    data["admin_messages"][str(admin_message.message_id)] = {
        "group_message_id": group_message.message_id,
        "user_id": user_id,
        "type": "withdrawal"
    }
    
    if "withdrawals" not in user_data:
        user_data["withdrawals"] = []
    
    user_data["withdrawals"].append({
        "amount": withdraw_amount,
        "date": str(datetime.now()),
        "status": "pending"
    })
    
    save_data(data)
    
    await query.edit_message_text(
        f"✅ درخواست برداشت شما به مبلغ {withdraw_amount:,} تومان دریافت شد و در حال بررسی است.\n\n"
        "پس از تأیید ادمین، مبلغ به کارت بانکی شما واریز خواهد شد."
    )
    await show_main_menu(user_id, context, first_time=False)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش اطلاعات پشتیبانی"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"برای ارتباط با پشتیبانی می‌توانید از راه‌های زیر استفاده کنید:\n\n"
        f"📲 تلگرام پشتیبانی:\n"
        f"{SUPPORT_USERNAME}\n\n"
        f"💬 واتساپ:\n"
        f"{WHATSAPP}\n\n"
        f"📸 اینستاگرام:\n"
        f"{INSTAGRAM}\n\n"
        f"☎️ پشتیبانی تلفنی:\n"
        f"{SUPPORT_PHONE}\n\n"
        f"🛍️ فروشگاه اینترنتی:\n"
        f"{SHOP_URL}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    await track_message(str(query.from_user.id), "support", query.message.message_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت پیام‌های دریافتی"""
    user_id = str(update.effective_user.id)
    data = load_data()
    user_data = data["users"].get(user_id, {})
    
    if not user_data:
        await start(update, context)
        return
    
    status = user_data.get("status")
    
    if status == "pending_verification":
        await verify_code(update, context)
    elif status == "pending_order":
        await order_code(update, context)
    elif status == "active":
        await show_main_menu(user_id, context)
    else:
        await update.message.reply_text("⚠️ وضعیت حساب شما نامشخص است. لطفاً با پشتیبانی تماس بگیرید.")

async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all commands"""
    command = update.message.text.split()[0].lower()
    
    if command == "/start":
        await start(update, context)
    elif command == "/invite":
        await invite_friends(update, context)
    elif command == "/profile":
        await profile(update, context)
    elif command == "/card":
        await bank_card(update, context)
    elif command == "/commissions":
        await my_commissions(update, context)
    elif command == "/withdraw":
        await withdraw(update, context)
    elif command == "/support":
        await support(update, context)
    elif command == "/help":
        await help(update, context)
    else:
        await update.message.reply_text("⚠️ دستور نامعتبر است. لطفاً از منوی اصلی استفاده کنید.")

def main() -> None:
    """تابع اصلی اجرای ربات"""
    application = Application.builder().token(TOKEN).build()
    
    # تعریف هندلرهای مکالمه
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_FATHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_father_name)],
            GET_NATIONAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_national_id)],
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            GET_POSTAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_postal_code)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            VERIFY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_code)],
            ORDER_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_code)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    invite_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(get_friends_phones, pattern="^get_friends_phones$")],
        states={
            INVITE_1: [MessageHandler(filters.TEXT & ~filters.COMMAND, invite_1)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    bank_card_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bank_card, pattern="^bank_card$")],
        states={
            BANK_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, bank_card)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    withdraw_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw, pattern="^withdraw$")],
        states={},
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    edit_address_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_address, pattern="^edit_address$")],
        states={
            EDIT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_address)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    edit_postal_code_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_postal_code, pattern="^edit_postal_code$")],
        states={
            EDIT_POSTAL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_postal_code)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    complete_commission_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(complete_commission, pattern="^complete_commission$")],
        states={
            COMPLETE_COMMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_complete_commission)],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    admin_reply_handler = MessageHandler(
        filters.TEXT & filters.Chat(chat_id=ADMIN_ID) & filters.REPLY,
        handle_admin_reply
    )
    
    # اضافه کردن هندلرها به اپلیکیشن
    application.add_handler(registration_handler)
    application.add_handler(invite_handler)
    application.add_handler(bank_card_handler)
    application.add_handler(withdraw_handler)
    application.add_handler(edit_address_handler)
    application.add_handler(edit_postal_code_handler)
    application.add_handler(complete_commission_handler)
    application.add_handler(admin_reply_handler)
    
    # اضافه کردن هندلرهای callback
    application.add_handler(CallbackQueryHandler(invite_friends, pattern="^invite_friends$"))
    application.add_handler(CallbackQueryHandler(get_invite_link, pattern="^get_invite_link$"))
    application.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(subsets, pattern="^subsets$"))
    application.add_handler(CallbackQueryHandler(my_commissions, pattern="^my_commissions$"))
    application.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))
    application.add_handler(CallbackQueryHandler(help, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(resend_verification, pattern="^resend_verification$"))
    
    # اضافه کردن هندلرهای پیام
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # اضافه کردن هندلر دستورات
    application.add_handler(CommandHandler(['start', 'invite', 'profile', 'card', 'commissions', 'withdraw', 'support', 'help'], command_handler))
    
    print("✅ ربات در حال اجراست.")
    application.run_polling()

if __name__ == '__main__':
    main()
