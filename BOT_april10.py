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
DB_FOLDER = Path(r"/mnt/")  # мой путь
DB_FOLDER.mkdir(parents=True, exist_ok=True)  # Создаем папку если её нет
DB_PATH = DB_FOLDER / "bot_messages.db"  # Полный путь к файлу БД
SUGGESTIONS_DB_PATH = DB_FOLDER / "suggestions.db"  # База для предложений

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния бота
CATEGORY, QUESTION, SUGGESTION = range(3)

# Константа для кнопки "Назад"
BACK_BUTTON = "⬅️ Назад"

# Данные бота (12 категорий + вопросы)
bot_data = {
    "Склад": {
        "Что делать если я опоздал(до часа)?": "🔹 **Ответ:** При опоздании сотрудники ГК информируют об этом своих руководителей.\nСотрудник ОКК фиксирует опоздание сотрудника на основании данных, полученных при контроле системы СКУД. Сотрудник ОКК делает информационные рассылки писем по фактам опозданий еженедельно и по окончанию отчетного месяца руководителям подразделений согласно стандарту на процесс П2-01 «Контроль качества работы».",
        "Я потерял/забыл пропуск": "🔹 **Ответ:** Если сотрудник потерял/забыл индивидуальную бесконтактную карту доступа, то он может войти на площадку/в офис вместе с другим сотрудником ГК.\n По приходу на рабочее место сотрудник оформляет СЗ, выбрав в ПО 1С в разделе «Служебные записки» шаблон: «Заявка на выдачу пропуска (бесконтактной карты)». \nВ данную СЗ сотрудник вносит информацию об отсутствии индивидуальной бесконтактной карты и указывает дату, фамилию, инициалы сотрудника, вместе с которым он вошел в офис или чью индивидуальную бесконтактную карту он использовал при входе, затем лично обращается в ДУП для получения новой или временной индивидуальной бесконтактной карты. \nЗапрашивать и вкладывать изображение с фотофиксацией входа/выхода в данном случае не требуется. ",
        "Я заболел, но смогу выздороветь в течение 2х дней": "🔹 **Ответ:**  Если вы заболеваете и не берете официальный больничный, то в этом случае вам необходимо оформить административный отпуск.\nСотруднику, берущему административный, либо руководителю сотрудника необходимо уведомить всех заинтересованных лиц до начала рабочего времени:\n через WhatsApp - специалиста по кадрам - 8 (962) 511-13-71;\n- ОКК - 8 (960) 198-07-72;\nлюбым удобным способом - колл-центр (для отдела продаж, при необходимости);\nлибо уведомить сотрудников ГК через общий чат GeoSM в Rocket.Chat. \nОтветственность за предоставление информации несет руководитель сотрудника.",
        "Мне необходимо уйти раньше с работы": "🔹 **Ответ:** В случае завершения рабочего дня ранее положеного времени по согласованию с руководителем необходимо оформить СЗ на административный отпуск на тот промежуток времени, который вам нужен.",
        "Почему ARM меняется в течении дня?": "🔹 **Ответ:** Данное явление связано с увеличением машин в расписании (согласованные машины день в день: отдел логистики находит машину менеджерам именно в этот день)",
        "Я не прошел алкотестер": "🔹 **Ответ:** Необходимо уведомить руководителя о сложившейся ситуации, затем следовать его инструкциям.\nДля руководителей: в первую очередь необходимо написать СЗ в 1С о сложившейся ситуации за сотрудника."
    },
    "Закупки": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "ОПП": {
         "Я потерял/забыл пропуск": "🔹 **Ответ:** Если сотрудник потерял/забыл индивидуальную бесконтактную карту доступа, то он может войти на площадку/в офис вместе с другим сотрудником ГК.\n По приходу на рабочее место сотрудник оформляет СЗ, выбрав в ПО 1С в разделе «Служебные записки» шаблон: «Заявка на выдачу пропуска (бесконтактной карты)». \nВ данную СЗ сотрудник вносит информацию об отсутствии индивидуальной бесконтактной карты и указывает дату, фамилию, инициалы сотрудника, вместе с которым он вошел в офис или чью индивидуальную бесконтактную карту он использовал при входе, затем лично обращается в ДУП для получения новой или временной индивидуальной бесконтактной карты. \nЗапрашивать и вкладывать изображение с фотофиксацией входа/выхода в данном случае не требуется. ",
        "Как оформить командировку?": "🔹 **Ответ:** 1. При получении от руководителя информации о командировке сотрудник планирует даты так, чтобы они не приходились на выходные/праздники\n2. Создание ЗК в 1С:\n- Статус 'черновик' → 'создан' после подтверждения\n- Заполнение обязательных полей по приложению 4\n- Проверка только на статусе 'создан'\n3. Уведомление кадров:\n- Минимум за 2 рабочих дня\n- С указанием номера ЗК\n4. Оформление приказа:\n- Форма по приложению 5\n- Срок: в день уведомления или следующий рабочий день\n5. Процедура подписания:\n- Получение по email → печать → подпись → скан в ЗК\n- Лично в ДУП → подпись → скан в ЗК → возврат оригинала\n6. Срочная командировка:\n- Руководитель вкладывает скан приказа\n7. Уведомление руководителя через обсуждения в 1С\n8. Согласование руководителем → статус 'согласовано'\n9. Заблаговременная командировка (от 2 дней):\n- Уведомление помощника директора с номером ЗК\n10. Оформление РДС помощником директора:\n- Привязка к ЗК\n- Исключение: отдел проектных продаж\n11. Срочная командировка:\n- Создание РДС сотрудником/руководителем\n- Контроль соответствия юрлица\n12. Согласование РДС руководителем\n13. Выдача средств:\n- Наличными/перевод на карту\n- Только при наличии приказа\n14. Сохранение всех документов о расходах\n15. Перенос дат:\n- Уведомление кадров и ОКК\n- Запрет самостоятельного изменения\n16. Корректировка ЗК:\n- Внесение изменений\n- Комментарий в обсуждениях\n- Новый скан приказа\n17. Отмена командировки:\n- Статус 'Отменен' → удаление\n- При привязанных документах → уведомление РОКК\n18. Возврат средств:\n- Уведомление бухгалтерии/руководителя/РОКК\n- Сверка расходов через авансовый отчет",
         "Где узнать про корпоративные мероприятия": "🔹 **Ответ:** Все анонсы мероприятий публикуются на портале в разделе Мероприятия, а также своевременно дублируются в Rocket Chat. Если у вас есть вопросы по корпративным мероприятиям или предложения, то вы можете обратиться к специалисту по корпоративной культуре в отдел маркетинга.",
    }, 
    "ЮРО": {
        "Где найти список сотрудников, работающих в определенном подразделении?": "🔹 **Советы:**\nдля поиска сотрудников существует 2 способа: \n1) на корпративном портале: в поисковой строек введите  полное название отдела и нажмите на кнопку поиск. По запросу вам выйдет список сотрудников конкретного отдела.\n2) в Rocket.chat намите кнопку каталог (книжка с решеткой), далее введите название отдела и нажмите на кнопку поиск.  По запросу вам выйдет список сотрудников конкретного отдела",
        "Где найти контактную информацию сотрудников / определенного сотрудника?": "🔹 **Советы:**\nДля поиска данных сотрудника существует 2 способа:\n1)На корпративном портале: в поисковой строек введите  полное название отдела и нажмите на кнопку поиск. По запросу вам выйдет список сотрудников конкретного отдела. В этом списке выбираете профиль необходимого сотрудника. В профиле найдете необходимые данные для связи.\n2)В Rocket.chat намите кнопку каталог (книжка с решеткой), далее введите название отдела и нажмите на кнопку поиск.По запросу вам выйдет список сотрудников конкретного отдела. В этом списке выбираете профиль необходимого сотрудника. Далее на открытой странице переписки с этим сотрудником нажимаете на его имя и в правой части под фото можете найти способ связи.",
        "Будет ли корпоративная библиотека пополняться книгами, что делать если хочу определенную книгу?": "🔹 **Ответ:** Корпративная библиотека пополняется регулярно. Завяки на определнные книги вы можете писать в Rocket.chat специалисту по корпративной культуре"
    },
    "ОП МСК": {
         "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "ОКК": {
        "Что делать если я опоздал(до часа)?": "🔹 **Ответ:** При опоздании сотрудники ГК информируют об этом своих руководителей.\nСотрудник ОКК фиксирует опоздание сотрудника на основании данных, полученных при контроле системы СКУД. Сотрудник ОКК делает информационные рассылки писем по фактам опозданий еженедельно и по окончанию отчетного месяца руководителям подразделений согласно стандарту на процесс П2-01 «Контроль качества работы».",
        "Что делать, если я не согласен с оценкой моей работы от отдела контроля качества?": "🔹 **Ответ:**\n Сотрудники ОКК только фиксируют несоответствия в работе сотрудников. Сотрудники отдела еженедельно рассылают все собранные данные руководителям подразделений,  у своего РОП менеджер может узнать результаты. При несогласии с результатми, можете обратиться к своему непосредственному руководителю.",
        "Когда выплачивают аванс?": "🔹 **Ответ:** Аванс выплачивается ежемесячно 25 числа текущего месяца.",
        "Когда будет выплачена зарплата за текущий месяц": "🔹 **Ответ:** Расчет и выплата заработной платы осуществляется два раза в месяц: 10 и 25 числа (10 число- заработная плата за предыдущий месяц, 25 число- аванс за нынешний месяц)",
    },
    "НЭП": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "Производство": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "ОП НН": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "Call-Центр": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "Логисты": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "ДУП": {
        "Вопросы в разработке": "🔹 Данный раздел вопросов еще в разработке",
    },
    "ППУ": {
        "Оставить предложение": "🔹 Напишите ваши предложения здесь и нажмите отправить"
    }
}

# ====== БАЗА ДАННЫХ ДЛЯ ЛОГИРОВАНИЯ ======
def init_db():
    """Инициализация базы данных для логов"""
    conn = sqlite3.connect(DB_PATH)
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
    
    # Инициализация базы для предложений
    conn = sqlite3.connect(SUGGESTIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            user_id INTEGER,
            username TEXT,
            suggestion TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(user_id: int, username: str, message: str):
    """Сохраняет сообщение в базу данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, username, message) VALUES (?, ?, ?)",
        (user_id, username, message)
    )
    conn.commit()
    conn.close()

def save_suggestion(user_id: int, username: str, suggestion: str):
    """Сохраняет предложение в базу данных"""
    conn = sqlite3.connect(SUGGESTIONS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO suggestions (user_id, username, suggestion) VALUES (?, ?, ?)",
        (user_id, username, suggestion)
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
        "👋 Привет! Я — бот-помощник. Если что-то не работает, то перезапусти бота нажатием на слово /start.\nДля взаимодействия со мной используй кнопки, выбирай категорию:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CATEGORY

async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора категории."""
    await log_message(update, context)
    user_choice = update.message.text
    
    if user_choice == BACK_BUTTON:
        return await start(update, context)
    
    if user_choice not in bot_data:
        await update.message.reply_text("⚠️ Ошибка: выбери категорию из кнопок")
        return CATEGORY
    
    context.user_data['category'] = user_choice
    
    # Особый случай для категории ППУ
    if user_choice == "ППУ":
        await update.message.reply_text(
            "🔹 Напишите ваши предложения здесь и нажмите отправить",
            reply_markup=ReplyKeyboardMarkup(
                [[BACK_BUTTON]], one_time_keyboard=True, resize_keyboard=True
            )
        )
        return SUGGESTION
    
    questions = list(bot_data[user_choice].keys())
    reply_keyboard = [questions[i:i+2] for i in range(0, len(questions), 2)]
    reply_keyboard.append([BACK_BUTTON])
    
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
    
    if user_choice == BACK_BUTTON:
        return await start(update, context)
    
    if not category or user_choice not in bot_data[category]:
        await update.message.reply_text("⚠️ Ошибка: вопрос не найден")
        return await start(update, context)
    
    answer = bot_data[category][user_choice]
    await update.message.reply_text(answer, parse_mode="Markdown")
    
    # Показываем те же вопросы с кнопкой "Назад"
    questions = list(bot_data[category].keys())
    reply_keyboard = [questions[i:i+2] for i in range(0, len(questions), 2)]
    reply_keyboard.append([BACK_BUTTON])
    
    await update.message.reply_text(
        "➡️ Выбери другой вопрос или вернись назад:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        )
    )
    return QUESTION

async def handle_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка предложений пользователей."""
    await log_message(update, context)
    user = update.message.from_user
    suggestion_text = update.message.text
    
    if suggestion_text == BACK_BUTTON:
        return await start(update, context)
    
    # Сохраняем предложение в отдельную базу
    save_suggestion(user.id, user.username or "нет_username", suggestion_text)
    
    await update.message.reply_text(
        "✅ Спасибо за ваше предложение! Оно сохранено и будет рассмотрено.",
        reply_markup=ReplyKeyboardMarkup(
            [[BACK_BUTTON]], one_time_keyboard=True, resize_keyboard=True
        )
    )
    return SUGGESTION

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
    init_db()  # Инициализируем обе базы данных
    
    application = Application.builder().token("7704376406:AAHbpP0wCuzk8U8VJSpq0w_odkIAJbHQxoE").build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, question)],
            SUGGESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_suggestion)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
