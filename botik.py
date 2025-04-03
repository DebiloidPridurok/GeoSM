from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import sqlite3
import logging
import os
from pathlib import Path

# ====== НАСТРОЙКА ПУТИ К БАЗЕ ДАННЫХ ======
DB_FOLDER = Path(r"//mnt/windows_share")  # мой путь
DB_FOLDER.mkdir(parents=True, exist_ok=True)  # Создаем папку если её нет
DB_PATH = DB_FOLDER / "bot_messages.db"  # Полный путь к файлу БД

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния бота
CATEGORY, QUESTION = range(2)

# Данные бота (12 категорий + вопросы)
bot_data = {
    "Склад": {
        "Что делать если я опоздал(до часа)?": "🔹 **Ответ:** При опоздании сотрудники ГК информируют об этом своих руководителей.  Сотрудник ОКК фиксирует опоздание сотрудника на основании данных, полученных при контроле системы СКУД. Сотрудник ОКК делает информационные рассылки писем по фактам опозданий еженедельно и по окончанию отчетного месяца руководителям подразделений согласно стандарту на процесс П2-01 «Контроль качества работы».",
        "Я потерял пропуск": "🔹 **Ответ:** Если сотрудник потерял/забыл индивидуальную бесконтактную карту доступа, то он может войти на площадку/в офис вместе с другим сотрудником ГК. По приходу на рабочее место сотрудник оформляет СЗ, выбрав в ПО 1С в разделе «Служебные записки» шаблон: «Заявка на выдачу пропуска (бесконтактной карты)». В данную СЗ сотрудник вносит информацию об отсутствии индивидуальной бесконтактной карты и указывает дату, фамилию, инициалы сотрудника, вместе с которым он вошел в офис или чью индивидуальную бесконтактную карту он использовал при входе, затем лично обращается в ДУП для получения новой или временной индивидуальной бесконтактной карты. Запрашивать и вкладывать изображение с фотофиксацией входа/выхода в данном случае не требуется. ",
        "Я заболел, но смогу выздороветь в течение 2х дней": "🔹 **Ответ:**  Если вы заболеваете и не берете официальный больничный, то в этом случае вам необходимо оформить административный отпуск. Сотруднику, берущему административный, либо руководителю сотрудника необходимо уведомить всех заинтересованных лиц до начала рабочего времени если вы заболеваете и не берете официальный больничный, то в этом случае вам необходимо оформить административный отпуск. Сотруднику, берущему административный, либо руководителю сотрудника необходимо уведомить всех заинтересованных лиц до начала рабочего времени: через WhatsApp- специалиста по кадрам - 8 (962) 511-13-71;- ОКК - 8 (960) 198-07-72;любым удобным способом- колл-центр (для отдела продаж, при необходимости); либо уведомить сотрудников ГК через общий чат GeoSM в Rocket.Chat. Ответственность за предоставление информации несет руководитель сотрудника.:через WhatsApp- специалиста по кадрам - 8 (962) 511-13-71;- ОКК - 8 (960) 198-07-72;любым удобным способом- колл-центр (для отдела продаж, при необходимости); либо уведомить сотрудников ГК через общий чат GeoSM в Rocket.Chat. Ответственность за предоставление информации несет руководитель сотрудника.",
   "Мне необходимо уйти раньше с работы": "🔹 **Ответ:** В случае завершения рабочего дня ранее положеного времени по согласованию с руководителем необходимо оформить СЗ на административный отпуск на тот промежуток времени, который вам нужен." },
    "Закупки": {
        "Мне необходимо уйти раньше с работы": "🔹 **Ответ:** ТОП-3:\n1. «Папа Джонс» (классическая)\n2. «DoDo Pizza» (тонкое тесто)\n3. «Пицца 22 см» (авторские рецепты)",
        "Как приготовить пасту карбонара?": "🔹 **Рецепт:**\n1. Обжарьте панчетту\n2. Добавьте яичные желтки + пармезан\n3. Смешайте с готовыми спагетти\n4. Подавайте сразу!",
    },
    "ОПП": {
        "Как поменять масло?": "🔹 **Инструкция:**\n1. Прогрейте двигатель 5 мин\n2. Слейте старое масло через пробку\n3. Залейте новое (5W-30 или 0W-20)\n4. Замените фильтр",
        "Почему горит Check Engine?": "🔹 **Возможные причины:**\n1. Неисправность датчика кислорода\n2. Проблемы с катализатором\n3. Бедная/богатая топливная смесь\n🔸 *Требуется диагностика*",
    },
    "ЮРО": {
        "Как выучить Python?": "🔹 **Советы:**\n1. Начните с основ на Stepik/Coursera\n2. Практикуйтесь на LeetCode\n3. Читайте документацию\n4. Пишите свои проекты",
        "Что такое API?": "🔹 **Объяснение:**\nAPI (Application Programming Interface) — это набор правил, позволяющий программам взаимодействовать между собой. Например, когда погодное приложение получает данные с сервера.",
    },
    "ОП МСК": {
        "Как прочистить трубы?": "🔹 **Способы:**\n1. Химия («Крот», «Мистер Мускул»)\n2. Вантуз (механическая чистка)\n3. Сантехнический трос (для сложных засоров)",
        "Как поклеить обои?": "🔹 **Инструкция:**\n1. Выровняйте стены шпаклевкой\n2. Нанесите клей на полотно\n3. Разгладьте от центра к краям\n4. Обрежьте излишки",
    },
    "ОКК": {
        "Как накопить на квартиру?": "🔹 **Стратегия:**\n1. Откладывайте 20-30% дохода\n2. Инвестируйте в ETF (например, S&P 500)\n3. Используйте вклад с капитализацией\n4. Сократите ненужные расходы",
        "Где взять кредит под низкий %?": "🔹 **Варианты:**\n1. Сбербанк (от 8.9% годовых)\n2. Тинькофф (онлайн-заявка)\n3. Альфа-Банк (для зарплатных клиентов)",
    },
    "НЭП": {
        "Куда поехать в Турции?": "🔹 **Маршрут:**\n1. Стамбул (Айя-София, Голубая мечеть)\n2. Каппадокия (воздушные шары)\n3. Анталия (пляжи Клеопатры)",
        "Как получить шенгенскую визу?": "🔹 **Документы:**\n1. Загранпаспорт\n2. Страховка (покрытие €30k+)\n3. Бронь отеля\n4. Выписка с работы\n5. Фото 3.5×4.5 см",
    },
    "Производство": {
        "Как подготовиться к ЕГЭ?": "🔹 **План:**\n1. Решайте варианты на «РешуЕГЭ»\n2. Разбирайте ошибки с репетитором\n3. Пишите эссе по шаблону\n4. Учите теорию по темам",
        "Где учиться на программиста?": "🔹 **Варианты:**\n1. ВУЗы: МФТИ, ВШЭ, СПбГУ\n2. Онлайн-курсы: Яндекс.Практикум, Hexlet\n3. Зарубежные университеты (MIT, Stanford)",
    },
    "ОП НН": {
        "Как сбить высокую температуру?": "🔹 **Методы:**\n1. Парацетамол (1 таблетка)\n2. Обильное питье (вода, морс)\n3. Прохладный компресс на лоб\n🔸 *Если >39°C — вызывайте врача*",
        "Что делать при простуде?": "🔹 **Рекомендации:**\n1. Постельный режим\n2. Чай с лимоном и медом\n3. Промывание носа солевым раствором\n4. Витамин C (1000 мг/день)",
    },
    "Call-Центр": {
        "Где купить PS5 дешевле?": "🔹 **Магазины:**\n1. DNS (акции в черную пятницу)\n2. Wildberries (с кэшбэком)\n3. Avito (б/у, но проверяйте при встрече)",
        "Как пройти Elden Ring?": "🔹 **Советы:**\n1. Качайте уровень (фармите руны)\n2. Используйте «духов пепла» для сложных боссов\n3. Изучайте слабые места противников",
    },
    "Логисты": {
        "Как вернуть товар в магазин?": "🔹 **Правила:**\n1. Сохраняйте чек\n2. Обратитесь в течение 14 дней\n3. Товар должен быть в оригинальной упаковке\n4. Напишите заявление",
        "Как выбрать ноутбук для работы?": "🔹 **Критерии:**\n1. Процессор: Intel Core i5/i7 или Ryzen 5/7\n2. ОЗУ: 16 ГБ (минимум 8 ГБ)\n3. SSD: 512 ГБ\n4. Экран: IPS, 15.6 дюймов",
    },
    "ДУП": {
        "Как познакомиться в интернете?": "🔹 **Советы:**\n1. Будьте искренними в анкете\n2. Пишите персонализированные сообщения (не «Привет»)\n3. Предложите встречу после недели общения",
        "Как пережить расставание?": "🔹 **Способы:**\n1. Удалите бывшего из соцсетей\n2. Займитесь спортом\n3. Найдите новое хобби\n4. Обратитесь к психологу при необходимости",
    }
}

# ====== БАЗА ДАННЫХ ДЛЯ ЛОГИРОВАНИЯ ======
def init_db():
    """Инициализация базы данных для логов"""
    conn = sqlite3.connect(DB_PATH)  # Теперь используем указанный путь
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            user_id INTEGER,
            username TEXT,
            message TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(user_id: int, username: str, message: str):
    """Сохраняет сообщение в базу данных"""
    conn = sqlite3.connect(DB_PATH)  # И здесь тоже
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, username, message) VALUES (?, ?, ?)",
        (user_id, username, message)
    )
    conn.commit()
    conn.close()

# ====== ОСНОВНЫЕ ФУНКЦИИ БОТА ======
async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Логирует сообщение"""
    user = update.message.from_user
    message_text = update.message.text
    save_message(user.id, user.username or "нет_username", message_text)
    logger.info(f"Сообщение от {user.id}: {message_text}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы бота - выбор категории."""
    await log_message(update, context)
    context.user_data.clear()
    
    categories = list(bot_data.keys())
    reply_keyboard = [categories[i:i+3] for i in range(0, len(categories), 3)]
    
    await update.message.reply_text(
        "👋 Привет! Я — бот-помощник. Выбери категорию:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CATEGORY

async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора категории."""
    await log_message(update, context)
    user_choice = update.message.text
    
    if user_choice not in bot_data:
        await update.message.reply_text("⚠️ Ошибка: выбери категорию из кнопок")
        return CATEGORY
    
    context.user_data['category'] = user_choice
    questions = list(bot_data[user_choice].keys())
    reply_keyboard = [questions[i:i+2] for i in range(0, len(questions), 2)]
    
    await update.message.reply_text(
        f"🗂 Категория: <b>{user_choice}</b>\nВыбери вопрос:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
        parse_mode="HTML"
    )
    return QUESTION

async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбранного вопроса."""
    await log_message(update, context)
    user_choice = update.message.text
    category = context.user_data.get('category')
    
    if not category or user_choice not in bot_data[category]:
        await update.message.reply_text("⚠️ Ошибка: вопрос не найден")
        return await start(update, context)
    
    answer = bot_data[category][user_choice]
    await update.message.reply_text(answer, parse_mode="Markdown")
    await update.message.reply_text("➡️ Хочешь задать ещё вопрос? Нажми /start")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога."""
    await update.message.reply_text(
        "❌ Диалог прерван. Чтобы начать заново, нажми /start",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Ошибка: {context.error}")

# ====== ЗАПУСК БОТА ======
def main() -> None:
    """Запуск бота."""
    init_db()
    
    application = Application.builder().token("7704376406:AAHbpP0wCuzk8U8VJSpq0w_odkIAJbHQxoE").build()
    
    # Основной обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
