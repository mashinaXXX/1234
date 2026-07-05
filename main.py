import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any
import html
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ReplyKeyboardMarkup, \
    KeyboardButton, ErrorEvent
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('TOKEN')

CHANNEL_ID = -1003649569064

RATE_LIMIT_SECONDS = 1
last_request_time: Dict[int, float] = {}
MAX_MESSAGE_LENGTH = 50

# Паттерны для валидации телефона
PHONE_PATTERNS = [
    r'^\+?[1-9]\d{1,14}$',
    r'^\+7\d{10}$',
    r'^998\d{9}$',
    r'^992\d{9}$',
    r'^996\d{9}$',
    r'^\d{10,15}$',
]

# Ссылки (оставляем в тексте, но без предпросмотра)
LAW_URL = "http://publication.pravo.gov.ru/document/0001202412280045?index=1"
ROSOBR_URL = "https://obrnadzor.gov.ru/news/bolee-87-nesovershennoletnih-inostrannyh-grazhdan-pretenduyushhih-na-obuchenie-v-rossijskih-shkolah-ne-mogut-byt-zachisleny/"

# Кнопки выбора языка
LANGS = [
    ("ru", "🇷🇺 Русский"),
    ("uz", "🇺🇿 O'zbek"),
    ("tg", "🇹🇯 Тоҷикӣ"),
    ("ky", "🇰🇬 Кыргызча"),
    ("en", "🇬🇧 English"),
]

LANG_NAMES = dict(LANGS)

# === ТЕКСТЫ (обновлены по вашим требованиям) ===
TEXTS = {
    "ru": {
        1: (
            "Здравствуйте! Рады вас приветствовать в официальном телеграмм боте образовательного центра \"НУР\"! "
            f"С 1 апреля 2025 года согласно <a href=\"{LAW_URL}\">Федеральному закону №544</a> "
            "для поступления в школы иностранным гражданам необходимо сдать экзамен по русскому языку. "
            f"В 2025 году <a href=\"{ROSOBR_URL}\">согласно данным Рособрнадзора</a> "
            "почти 90% детей не смогли пройти тестирование и не поступили в школы.\n\n"
        ),
        2: (
            "В связи с чем, мы открываем набор на курсы по программам подготовки 1-11 класса для сдачи данного тестирования. "
            "Более подробная информация будет предоставлена на бесплатном вступительном занятии, который можно будет посетить очно (места ограничены) или онлайн.\n\n"
        ),
        3: (
            "Для регистрации на бесплатное занятие напишите в чате контактный номер телефона, далее менеджер с вами свяжется.\n\n"
        ),
    },

    "uz": {
        1: (
            "Assalomy alaykum! Sizni NUR ta'lim markazining rasmiy bot telegrammalarida kutib olishdan mamnunmiz! "
            "2025 yil 1 apreldagi "
            f"<a href=\"{LAW_URL}\">№544-FZ-sonli Federal qonuniga</a> "
            "maktablarga kirish uchun chet el fuqarolari rus tilidan imtihon topshirishlari kerak. "
            f"2025 yilda <a href=\"{ROSOBR_URL}\">Rosobrnadzor ma'lumotlariga ko'ra</a> "
            "bolalarning deyarli 90 foizi sinovdan o'ta olmadi va maktablarga kira olmadi.\n\n"
        ),
        2: (
            "Shu munosabat bilan biz ushbu testni topshirish uchun 1-11-sinflar uchun o'quv dasturlari bo'yicha kurslarga qabulni ochamiz. "
            "Batafsil ma'lumotni shaxsan (joylar soni cheklangan) yoki onlayn tarzda qatnashishingiz mumkin bo'lgan bepul kirish darsida olishingiz mumkin.\n\n"
        ),
        3: (
            "Bepul darsga yozilish uchun chatda telefon raqamingizni yozing va menejer siz bilan bog'lanadi.\n\n"
        ),
    },

    "tg": {
        1: (
            "Салом! Хуш омадед ба телеграммаи расмии маркази таълимии нур! Аз 1 апрели соли 2025 тибқи қонуни Федеролии "
            f"<a href=\"{LAW_URL}\">№544</a> "
            "барои дохил шудан ба мактаб шаҳрвандони хориҷӣ бояд имтиҳони забони русиро супоранд. "
            f"Дар соли 2025, <a href=\"{ROSOBR_URL}\">Тибқи Маълумоти Рособрнадзор</a> "
            "почти 90% кӯдакон натавонистанд аз санҷиш гузаранд ва ба мактаб дохил нашуданд.\n\n"
        ),
        2: (
            "Дар робита ба ин, мо курсҳои омӯзишии синфҳои 1-11-ро барои супоридани ин санҷиш оғоз мекунем. "
            "Шумо метавонед маълумоти бештарро дар ҷаласаи муқаддимавии ройгон, ки шахсан дидан мумкин аст (шумораи ҷойҳо маҳдуд аст) е онлайн пайдо кунед.\n\n"
        ),
        3: (
            "Барои дохил шудан ба дарси ройгон, рақами телефони худро дар чат ворид кунед ва администратор бо шумо тамос мегирад.\n\n"
        ),
    },

    "ky": {
        1: (
            "Салам! Жарык билим берүү борборунун расмий телеграммасына кош келиңиз! 1-жылдын 2025-апрелинен тартып, весит "
            f"<a href=\"{LAW_URL}\">№544 Федералдык мыйзамына</a> "
            "ылайык чет өлкөлүк жарандар мектепке кирүү үчүн орус тили боюнча экзамен тапшырышы керек. "
            f"2025-жылы, <a href=\"{ROSOBR_URL}\">Рособрнадзордун айтымында</a> "
            "почти балдардын 90% тест тапшыра албай, мектепке кире албай калышты.\n\n"
        ),
        2: (
            "Ушуга байланыштуу биз бул тестти тапшыруу үчүн 1-11-класстарды даярдоо программалары боюнча курстарга кабыл алууну ачабыз. "
            "Толугураак маалымат акысыз кирүү сессиясында берилет, ал күндүзгү (орун чектөө) же онлайн режиминде болушу мүмкүн.\n\n"
        ),
        3: (
            "Акысыз сабакка жазылуу үчүн, чатка телефон номериңизди киргизиңиз, ошондо менеджер Сиз менен байланышат.\n\n"
        ),
    },

    "en": {
        1: (
            "Hi! Welcome to the official telegram of the Light Education Center! From April 1, 2025, in accordance with Federal Law "
            f"<a href=\"{LAW_URL}\">№544</a> "
            "Foreign citizens must pass the Russian language exam in order to enroll in school. "
            f"In 2025, <a href=\"{ROSOBR_URL}\">according to Rosobrnadzor</a> "
            "almost 90% of the children failed the test and were unable to enroll in school.\n\n"
        ),
        2: (
            "In this regard, we are accepting applications for 1-11 grade preparation courses for this test. "
            "More detailed information is provided during a free login session, which can be held in the day department (limited space) or online.\n\n"
        ),
        3: (
            "To register for a free class, write your contact phone number in the chat, and the manager will contact you.\n\n"
        ),
    },
}

# Словарь для отслеживания состояния пользователей
user_states: Dict[int, Dict[str, Any]] = {}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def validate_phone_number(phone: str) -> bool:
    """Валидация номера телефона"""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    for pattern in PHONE_PATTERNS:
        if re.match(pattern, phone):
            return True

    return False


def sanitize_input(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Очистка пользовательского ввода"""
    if not text:
        return ""

    text = text[:max_length]
    text = html.escape(text)
    text = ' '.join(text.split())

    return text


def check_rate_limit(user_id: int) -> bool:
    """Проверка ограничения на частоту запросов"""
    current_time = datetime.now().timestamp()

    if user_id in last_request_time:
        time_diff = current_time - last_request_time[user_id]
        if time_diff < RATE_LIMIT_SECONDS:
            return False

    last_request_time[user_id] = current_time
    return True


def is_valid_channel_id(channel_id: int) -> bool:
    """Проверка валидности ID канала"""
    return isinstance(channel_id, int) and channel_id < 0


def get_help_keyboard() -> ReplyKeyboardMarkup:
    """Custom keyboard с кнопкой Помощь"""
    keyboard = [
        [KeyboardButton(text="🆘 Помощь / Help")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Нажмите кнопку для помощи..."
    )


def lang_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора языка"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"lang:{code}")]
            for code, label in LANGS
        ]
    )


def nav_keyboard(lang: str, page: int) -> InlineKeyboardMarkup:
    """Клавиатура для навигации по страницам"""
    buttons = []

    # Тексты кнопок на разных языках
    back_texts = {
        "ru": "⬅️ Назад",
        "uz": "⬅️ Orqaga",
        "tg": "⬅️ Бозгашт",
        "ky": "⬅️ Артка",
        "en": "⬅️ Back"
    }

    next_texts = {
        "ru": "Далее ➡️",
        "uz": "Keyingi ➡️",
        "tg": "Баъдӣ ➡️",
        "ky": "Кийинки ➡️",
        "en": "Next ➡️"
    }

    if page > 1:
        left = InlineKeyboardButton(
            text=back_texts.get(lang, "⬅️ Back"),
            callback_data=f"prev:{lang}:{page}"
        )
    else:
        left = InlineKeyboardButton(
            text=back_texts.get(lang, "⬅️ Back"),
            callback_data="back:langs"
        )

    buttons.append(left)

    if page < 3:
        right = InlineKeyboardButton(
            text=next_texts.get(lang, "Next ➡️"),
            callback_data=f"next:{lang}:{page}"
        )
        buttons.append(right)

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def get_start_text(lang: str = "ru") -> str:
    """Текст с командой /start для повторного запуска"""
    start_texts = {
        "ru": "\n\n🔁 Чтобы начать заново, отправьте: /start",
        "uz": "\n\n🔁 Qayta boshlash uchun yuboring: /start",
        "tg": "\n\n🔁 Барои оғози нав, фиристед: /start",
        "ky": "\n\n🔁 Кайра баштоо үчүн жибериңиз: /start",
        "en": "\n\n🔁 To start over, send: /start"
    }
    return start_texts.get(lang, start_texts["ru"])


def get_help_text(lang: str = "ru") -> str:
    """Текст помощи на разных языках"""
    help_texts = {
        "ru": (
            "🆘 <b>Помощь</b>\n\n"
            "• Отправьте <b>/start</b> для начала работы с ботом\n"
            "• Выберите язык для просмотра информации о курсах\n"
            "• Листайте страницы с помощью кнопок навигации\n"
            "• На 3-й странице укажите номер телефона для связи с менеджером\n\n"
            "📞 <b>Ваши контакты будут отправлены менеджеру для обратной связи.</b>\n\n"
            "🔒 <i>Ваши данные защищены. Бот не хранит личную информацию.</i>"
        ),
        "uz": (
            "🆘 <b>Yordam</b>\n\n"
            "• Bot bilan ishlashni boshlash uchun <b>/start</b> ni yuboring\n"
            "• Kurslar haqida ma'lumotni ko'rish uchun tilni tanlang\n"
            "• Navigatsiya tugmalari yordamida sahifalarni aylantiring\n"
            "• 3-sahifada menejer bilan aloqaga chiqish uchun telefon raqamingizni ko'rsating\n\n"
            "📞 <b>Aloqa uchun ma'lumotlaringiz menejerga yuboriladi.</b>\n\n"
            "🔒 <i>Ma'lumotlaringiz himoyalangan. Bot shaxsiy ma'lumotlarni saqlamaydi.</i>"
        ),
        "tg": (
            "🆘 <b>Кумак</b>\n\n"
            "• Барои кор бо бот оғоз кардан, <b>/start</b> фиристед\n"
            "• Маълумотро дар бораи курсҳо дидан барои забони интихоб кунед\n"
            "• Тугмаҳои навигатсия барои саҳифаҳо гардонед\n"
            "• Дар саҳифаи 3 рақами телефони худро барои тамос бо менеҷер гузоред\n\n"
            "📞 <b>Маълумоти тамоси шумо ба менеҷер фиристода мешавад.</b>\n\n"
            "🔒 <i>Маълумоти шумо мухофизат карда мешавад. Бот маълумоти шахсиро нигоҳ намедорад.</i>"
        ),
        "ky": (
            "🆘 <b>Жардам</b>\n\n"
            "• Бот менен иштөөнү баштоо үчүн <b>/start</b> жибериңиз\n"
            "• Курстар жөнүндө маалыматты көрүү үчүн тилди тандаңыз\n"
            "• Навигация баскычтары менен барактарды которуңуз\n"
            "• 3-баракта менеджер менен байланышуу үчүн телефон номериңизди көрсөтүңүз\n\n"
            "📞 <b>Байланыш маалыматтарыңыз менеджерге жиберилет.</b>\n\n"
            "🔒 <i>Маалыматтарыңыз корголгон. Бот жеке маалыматтарды сактабайт.</i>"
        ),
        "en": (
            "🆘 <b>Help</b>\n\n"
            "• Send <b>/start</b> to start working with the bot\n"
            "• Select a language to view information about courses\n"
            "• Scroll through pages using navigation buttons\n"
            "• On page 3, indicate your phone number to contact the manager\n\n"
            "📞 <b>Your contact information will be sent to the manager.</b>\n\n"
            "🔒 <i>Your data is protected. The bot does not store personal information.</i>"
        )
    }
    return help_texts.get(lang, help_texts["ru"])


# === ОТВЕТЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===
RESPONSES = {
    "success": {
        "ru": "✅ Спасибо! Ваш номер телефона получен. Менеджер свяжется с вами в ближайшее время.",
        "uz": "✅ Rahmat! Telefon raqamingiz qabul qilindi. Menejer tez orada siz bilan bog'lanadi.",
        "tg": "✅ Ташаккур! Рақами телефони шумо гирифта шуд. Менеҷер ба зудӣ бо шумо тамос мегирад.",
        "ky": "✅ Рахмат! Телефон номериңиз кабыл алынды. Менеджер жакын арада сиз менен байланышат.",
        "en": "✅ Thank you! Your phone number has been received. The manager will contact you shortly."
    },
    "error": {
        "ru": "❌ Произошла ошибка при отправке данных. Пожалуйста, попробуйте позже или свяжитесь с менеджером напрямую.",
        "uz": "❌ Ma'lumotlarni yuborishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring yoki menejer bilan bevosita bog'laning.",
        "tg": "❌ Дар фиристодани маълумот хатогӣ ба амал омад. Лутфан, дертар кӯшиш кунед ё бо менеҷер бевосита тамос гиред.",
        "ky": "❌ Маалыматтарды жөнөтүүдө ката кетти. Сураныч, кийинчерэек аракет кылыңыз же менеджер менен түздөн-түз байланышыңыз.",
        "en": "❌ An error occurred while sending data. Please try again later or contact the manager directly."
    },
    "rate_limit": {
        "ru": "⏳ Вы отправляете сообщения слишком часто. Пожалуйста, подождите немного.",
        "uz": "⏳ Siz xabarlarni juda tez-tez yuboryapsiz. Iltimos, bir oz kuting.",
        "tg": "⏳ Шумо паёмҳоро аз ҳад зиёд фиристода истодаед. Лутфан, каме интизор шавед.",
        "ky": "⏳ Сиз билдирүүлөрдү өтө тез жибересиз. Сураныч, бир аз күтө туруңуз.",
        "en": "⏳ You are sending messages too often. Please wait a moment."
    },
    "invalid_phone": {
        "ru": "❌ Пожалуйста, введите корректный номер телефона. Пример: +79991234567 или 998901234567",
        "uz": "❌ Iltimos, to'g'ri telefon raqamini kiriting. Misol: +79991234567 yoki 998901234567",
        "tg": "❌ Лутфан, рақами телефони дурустро ворид кунед. Мисол: +79991234567 ё 992901234567",
        "ky": "❌ Сураныч, туура телефон номерин киргизиңиз. Мисал: +79991234567 же 996701234567",
        "en": "❌ Please enter a valid phone number. Example: +79991234567 or 998901234567"
    },
    "welcome": {
        "ru": "👋 <b>Добро пожаловать в образовательный центр \"НУР\"!</b>\n\n"
              "🔒 Ваши данные защищены. Бот не хранит личную информацию.\n\n"
              "👇 <b>Пожалуйста, выберите язык интерфейса:</b>",
        "uz": "👋 <b>NUR ta'lim markaziga xush kelibsiz!</b>\n\n"
              "🔒 Ma'lumotlaringiz himoyalangan. Bot shaxsiy ma'lumotlarni saqlamaydi.\n\n"
              "👇 <b>Iltimos, interfeys tilini tanlang:</b>",
        "tg": "👋 <b>Маркази таълимии \"НУР\" хуш омадед!</b>\n\n"
              "🔒 Маълумоти шумо мухофизат карда мешавад. Бот маълумоти шахсиро нигоҳ намедорад.\n\n"
              "👇 <b>Лутфан, забони интерфейсро интихоб кунед:</b>",
        "ky": "👋 <b>Жарык билим берүү борборуна кош келиңиз!</b>\n\n"
              "🔒 Маалыматтарыңыз корголгон. Бот жеке маалыматтарды сактабайт.\n\n"
              "👇 <b>Сураныч, интерфейс тилин тандаңыз:</b>",
        "en": "👋 <b>Welcome to the educational center \"NUR\"!</b>\n\n"
              "🔒 Your data is protected. The bot does not store personal information.\n\n"
              "👇 <b>Please select the interface language:</b>"
    }
}


async def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)

    # Проверка конфигурации
    if not BOT_TOKEN or BOT_TOKEN == "my_token":
        logger.error("❌ ОШИБКА: Токен бота не задан. Укажите его в .env как TOKEN=...")
        print("❌ ОШИБКА: Токен бота не задан. Укажите его в .env как TOKEN=...")
        return

    if not is_valid_channel_id(CHANNEL_ID):
        logger.error("❌ ОШИБКА: Некорректный ID канала!")
        print("❌ ОШИБКА: Некорректный ID канала!")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    # Бот рассчитан на личные сообщения — не реагируем в группах/каналах,
    # куда его может добавить кто угодно (спам в CHANNEL_ID, лишняя нагрузка)
    dp.message.filter(F.chat.type == "private")
    dp.callback_query.filter(F.message.chat.type == "private")

    @dp.message(CommandStart())
    async def start_command(message: Message):
        """Обработчик команды /start - всегда показываем выбор языка"""
        if not check_rate_limit(message.from_user.id):
            return

        user_id = message.from_user.id

        # Очищаем предыдущее состояние пользователя
        if user_id in user_states:
            del user_states[user_id]

        # Показываем custom keyboard с кнопкой помощи
        await message.answer(
            "👇 Используйте кнопку ниже для помощи в любое время:",
            reply_markup=get_help_keyboard()
        )

        # Приветственное сообщение и сразу выбор языка
        welcome_text = RESPONSES["welcome"]["ru"]

        # Отправляем клавиатуру с выбором языка
        await message.answer(
            welcome_text,
            reply_markup=lang_keyboard(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    @dp.message(F.text == "🆘 Помощь / Help")
    async def help_button_handler(message: Message):
        """Обработчик нажатия кнопки Помощь"""
        if not check_rate_limit(message.from_user.id):
            return

        # Определяем язык пользователя
        user_id = message.from_user.id
        lang = user_states.get(user_id, {}).get("lang", "ru")

        # Отправляем помощь на нужном языке
        await message.answer(
            get_help_text(lang),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    @dp.message(Command("help"))
    async def help_command_handler(message: Message):
        """Обработчик команды /help"""
        if not check_rate_limit(message.from_user.id):
            return

        # Определяем язык пользователя
        user_id = message.from_user.id
        lang = user_states.get(user_id, {}).get("lang", "ru")

        # Отправляем помощь на нужном языке
        await message.answer(
            get_help_text(lang),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    @dp.callback_query(F.data.startswith("lang:"))
    async def choose_lang(cb: CallbackQuery):
        """Выбор языка"""
        try:
            lang = cb.data.split(":", 1)[1]
            if lang not in TEXTS:
                await cb.answer("❌ Язык не поддерживается")
                return

            user_states[cb.from_user.id] = {"lang": lang, "page": 1}
            # Отправляем текст БЕЗ предпросмотра ссылок
            await cb.message.edit_text(
                TEXTS[lang][1],
                reply_markup=nav_keyboard(lang, 1),
                disable_web_page_preview=True
            )
            await cb.answer()
        except Exception as e:
            logger.error(f"Ошибка в choose_lang: {e}")
            await cb.answer("❌ Произошла ошибка")

    @dp.callback_query(F.data == "back:langs")
    async def back_to_langs(cb: CallbackQuery):
        """Возврат к выбору языка"""
        try:
            # Определяем язык для приветствия
            user_id = cb.from_user.id
            lang = user_states.get(user_id, {}).get("lang", "ru")

            welcome_text = RESPONSES["welcome"].get(lang, RESPONSES["welcome"]["ru"])

            await cb.message.edit_text(
                welcome_text,
                reply_markup=lang_keyboard(),
                disable_web_page_preview=True
            )
            await cb.answer()
        except Exception as e:
            logger.error(f"Ошибка в back_to_langs: {e}")
            await cb.answer("❌ Произошла ошибка")

    @dp.callback_query(F.data.startswith("next:"))
    async def next_page(cb: CallbackQuery):
        """Следующая страница"""
        try:
            _, lang, page_str = cb.data.split(":")
            page = int(page_str) + 1

            if lang not in TEXTS or page not in TEXTS[lang]:
                await cb.answer("❌ Страница не найдена")
                return

            user_states[cb.from_user.id] = {"lang": lang, "page": page}
            await cb.message.edit_text(
                TEXTS[lang][page],
                reply_markup=nav_keyboard(lang, page),
                disable_web_page_preview=True
            )
            await cb.answer()
        except Exception as e:
            logger.error(f"Ошибка в next_page: {e}")
            await cb.answer("❌ Произошла ошибка")

    @dp.callback_query(F.data.startswith("prev:"))
    async def prev_page(cb: CallbackQuery):
        """Предыдущая страница"""
        try:
            _, lang, page_str = cb.data.split(":")
            page = int(page_str) - 1

            if lang not in TEXTS or page not in TEXTS[lang]:
                await cb.answer("❌ Страница не найдена")
                return

            user_states[cb.from_user.id] = {"lang": lang, "page": page}
            await cb.message.edit_text(
                TEXTS[lang][page],
                reply_markup=nav_keyboard(lang, page),
                disable_web_page_preview=True
            )
            await cb.answer()
        except Exception as e:
            logger.error(f"Ошибка в prev_page: {e}")
            await cb.answer("❌ Произошла ошибка")

    @dp.message(F.text)
    async def handle_phone_input(message: Message):
        """Обработчик ввода номера телефона"""
        user_id = message.from_user.id

        # Проверка ограничения на частоту запросов
        if not check_rate_limit(user_id):
            lang = user_states.get(user_id, {}).get("lang", "ru")
            await message.answer(RESPONSES["rate_limit"].get(lang, RESPONSES["rate_limit"]["ru"]))
            return

        # Проверяем, был ли пользователь на 3-й странице
        user_state = user_states.get(user_id)
        if not user_state or user_state["page"] != 3:
            # Если пользователь не на 3-й странице, проверяем ключевые слова
            text_lower = message.text.lower()
            start_keywords = ["старт", "start", "начать", "boshlash", "начинать", "go", "привет", "здравствуйте",
                              "помощь", "help"]

            if any(keyword in text_lower for keyword in start_keywords):
                # Если пользователь пишет что-то похожее на старт, начинаем заново
                await start_command(message)
            return

        phone = sanitize_input(message.text.strip())
        lang = user_state.get("lang", "ru")

        # Валидация номера телефона
        if not validate_phone_number(phone):
            await message.answer(RESPONSES["invalid_phone"].get(lang, RESPONSES["invalid_phone"]["ru"]))
            return

        try:
            # Формируем сообщение для канала
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            language_name = LANG_NAMES.get(lang, "Русский")

            safe_phone = html.escape(phone)
            safe_name = html.escape(message.from_user.full_name or "Не указано")

            channel_message = (
                f"📱 <b>НОВЫЙ ЗАПРОС</b>\n\n"
                f"🆔 <b>ID пользователя:</b> <code>{user_id}</code>\n"
                f"👤 <b>Имя:</b> {safe_name}\n"
            )

            if message.from_user.username:
                channel_message += f"🔗 <b>Username:</b> @{html.escape(message.from_user.username)}\n"

            channel_message += (
                f"📞 <b>Телефон:</b> <code>{safe_phone}</code>\n"
                f"🌐 <b>Язык интерфейса:</b> {language_name}\n"
                f"⏰ <b>Время:</b> {timestamp}\n\n"
                f"💬 <a href='tg://user?id={user_id}'>Написать пользователю</a>"
            )

            # Проверяем ID канала перед отправкой
            if not is_valid_channel_id(CHANNEL_ID):
                logger.error(f"Некорректный ID канала: {CHANNEL_ID}")
                raise ValueError("Некорректный ID канала")

            # Отправляем в канал
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=channel_message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            # Успешный ответ пользователю с командой для повторного запуска
            success_message = (
                f"{RESPONSES['success'].get(lang, RESPONSES['success']['ru'])}"
                f"{get_start_text(lang)}"
            )

            await message.answer(
                success_message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

            # Логируем успешную отправку
            logger.info(f"✅ Данные отправлены в канал {CHANNEL_ID} от пользователя {user_id}")

        except Exception as e:
            # Ошибка отправки
            error_msg = RESPONSES["error"].get(lang, RESPONSES["error"]["ru"])
            await message.answer(error_msg)

            # Логируем ошибку
            logger.error(f"❌ Ошибка отправки данных для пользователя {user_id}: {e}", exc_info=True)

    @dp.errors()
    async def error_handler(event: ErrorEvent):
        """Глобальный обработчик ошибок"""
        logger.error(f"Глобальная ошибка: {event.exception}", exc_info=event.exception)
        return True

    try:
        logger.info("🤖 Бот запускается...")
        print("🤖 Бот запущен и ожидает сообщений...")
        print("👉 Отправьте /start для начала работы")
        print("👉 Используйте кнопку '🆘 Помощь / Help' для помощи")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
