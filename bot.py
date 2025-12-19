import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен!")
    exit(1)

if not ADMIN_CHAT_ID:
    logger.error("❌ ADMIN_CHAT_ID не установлен!")
    exit(1)

# ==================== ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ ====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== ЛОКАЛЬНОЕ СОХРАНЕНИЕ В ФАЙЛ ====================
LOG_FILE = "requests.log"

def save_to_log_file(user_data: Dict[str, Any], request_id: str):
    """Сохраняет заявку в текстовый файл."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n{'='*60}\n")
            f.write(f"Заявка #{request_id} - {timestamp}\n")
            f.write(f"{'='*60}\n")
            f.write(f"👤 Имя: {user_data.get('name', '')}\n")
            f.write(f"📞 Контакт: {user_data.get('contact', '')}\n")
            f.write(f"🏢 Бизнес: {user_data.get('business', '')}\n")
            f.write(f"🎯 Цель: {user_data.get('purpose', '')}\n")
            f.write(f"💰 Бюджет: {user_data.get('budget', '')}\n")
            f.write(f"📝 Описание:\n{user_data.get('description', '')}\n")
            f.write(f"{'='*60}\n")
        logger.info(f"✅ Заявка {request_id} сохранена в {LOG_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в файл: {e}")
        return False

# ==================== СОСТОЯНИЯ БОТА (FSM) ====================
class BotRequest(StatesGroup):
    waiting_for_name = State()
    waiting_for_contact = State()
    waiting_for_business = State()
    waiting_for_purpose = State()
    waiting_for_description = State()
    waiting_for_budget = State()
    waiting_for_confirmation = State()

# ==================== ФУНКЦИЯ ПРОВЕРКИ ТАЙМАУТА ====================
async def check_timeout(state: FSMContext, message: types.Message = None) -> bool:
    """Проверяет, истекло ли время сессии (10 минут)."""
    user_data = await state.get_data()
    last_activity = user_data.get('last_activity')
    
    if last_activity:
        last_time = datetime.fromisoformat(last_activity)
        if datetime.now() - last_time > timedelta(minutes=10):
            if message:
                await message.answer(
                    "⏰ Сессия истекла из-за неактивности (10 минут).\n"
                    "Напишите /start для начала нового опроса."
                )
            await state.clear()
            return True
    return False

async def update_last_activity(state: FSMContext):
    """Обновляет время последней активности."""
    await state.update_data(last_activity=datetime.now().isoformat())

# ==================== КЛАВИАТУРЫ ====================
def get_purpose_keyboard():
    keyboard = InlineKeyboardBuilder()
    buttons = [
        ("🛍 Продажи", "purpose_sales"),
        ("📅 Запись", "purpose_booking"),
        ("💬 Поддержка", "purpose_support"),
        ("📚 Контент", "purpose_content"),
        ("📝 Другое", "purpose_other")
    ]
    for text, data in buttons:
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    return keyboard.adjust(2).as_markup()

def get_budget_keyboard():
    keyboard = InlineKeyboardBuilder()
    buttons = [
        ("Бесплатно (тест)", "budget_free"),
        ("до 1000₽/мес", "budget_1000"),
        ("1000-3000₽/мес", "budget_3000"),
        ("3000-5000₽/мес", "budget_5000"),
        ("5000₽+/мес", "budget_5000+"),
        ("Ещё не решил", "budget_unknown")
    ]
    for text, data in buttons:
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    return keyboard.adjust(2).as_markup()

def get_cancel_keyboard():
    """Клавиатура для отмены на любом этапе."""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="❌ Отменить опрос",
        callback_data="cancel_survey"
    ))
    return keyboard.as_markup()

# ==================== ОТПРАВКА УВЕДОМЛЕНИЙ ====================
async def send_request_to_admin(user_data: Dict[str, Any], user_id: int, request_id: str):
    """Отправляет заявку администратору в Telegram."""
    message = f"""
<b>🚀 Новая заявка #{request_id}</b>

👤 <b>Клиент:</b> {user_data.get('name', 'Не указано')}
📞 <b>Контакты:</b> {user_data.get('contact', 'Не указано')}
🏢 <b>Бизнес:</b> {user_data.get('business', 'Не указано')}
🎯 <b>Цель бота:</b> {user_data.get('purpose', 'Не указано')}
💰 <b>Бюджет:</b> {user_data.get('budget', 'Не указано')}
📝 <b>Описание:</b>
{user_data.get('description', 'Не указано')}

🆔 <b>User ID:</b> {user_id}
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}

📄 <b>Сохранено локально в файле:</b> {LOG_FILE}
"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="✅ Принять в работу",
        callback_data=f"accept_{user_id}"
    ))
    keyboard.add(InlineKeyboardButton(
        text="💬 Написать клиенту",
        url=f"tg://user?id={user_id}"
    ))
    
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode="HTML",
            reply_markup=keyboard.as_markup()
        )
        logger.info(f"📨 Заявка {request_id} отправлена админу")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки админу: {e}")
        return False

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = """
🤖 <b>Привет! Я создам Telegram-бота для вашего бизнеса</b>

<b>Процесс простой и быстрый:</b>
1. <i>Сейчас:</i> Определим задачу и функционал (5-7 минут)
2. <i>После заявки:</i> Разработаем и настроим бота (1-3 рабочих дня)
3. <i>Итог:</i> Вы получаете готового, работающего бота

<b>Поехали! Как вас зовут?</b>
"""
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(BotRequest.waiting_for_name)
    await update_last_activity(state)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
<b>🤖 BotForge - создание Telegram-ботов</b>

<b>Команды:</b>
/start - начать создание бота
/help - показать это сообщение
/cancel - отменить текущий опрос
/logs - получить файл с заявками (только для админа)

<b>Как это работает:</b>
1. Вы описываете, какой бот нужен
2. Мы анализируем потребности
3. Предлагаем оптимальное решение
4. Создаём и настраиваем бота
5. Вы получаете готового бота за 1-3 дня

<b>Контакты:</b>
Поддержка: @botforge_support
"""
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Нет активного опроса для отмены.")
        return
    
    await state.clear()
    await message.answer(
        "✅ Опрос отменен.\n\n"
        "Если хотите начать заново, напишите /start"
    )

# ==================== КОМАНДА ДЛЯ ПОЛУЧЕНИЯ ЛОГОВ (ТОЛЬКО АДМИН) ====================
@dp.message(Command("logs"))
async def cmd_logs(message: types.Message):
    """Отправляет файл с заявками только администратору."""
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        await message.answer("❌ Эта команда только для администратора.")
        return
    
    if not os.path.exists(LOG_FILE):
        await message.answer("📭 Файл с заявками пока пуст.")
        return
    
    try:
        with open(LOG_FILE, "rb") as f:
            await message.answer_document(
                types.BufferedInputFile(f.read(), filename="requests.log"),
                caption="📄 Файл со всеми заявками"
            )
        logger.info("📤 Админ запросил файл с заявками")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке файла: {e}")
        logger.error(f"Ошибка отправки логов админу: {e}")

# ==================== ОБРАБОТЧИК ОТМЕНЫ ПО КНОПКЕ ====================
@dp.callback_query(F.data == "cancel_survey")
async def cancel_survey(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "✅ Опрос отменен.\n\n"
        "Если хотите начать заново, напишите /start"
    )
    await callback.answer()

# ==================== ОБРАБОТЧИКИ ДИАЛОГА ====================
@dp.message(BotRequest.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    # Проверка таймаута
    if await check_timeout(state, message):
        return
    
    await state.update_data(name=message.text)
    await update_last_activity(state)
    
    await message.answer(
        f"Отлично, {message.text}! 📞\n"
        "Как с вами связаться? (Telegram @username, номер телефона или email)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_contact)

@dp.message(BotRequest.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    if await check_timeout(state, message):
        return
    
    await state.update_data(contact=message.text)
    await update_last_activity(state)
    
    await message.answer(
        "🏢 Чем занимается ваш бизнес? (Например: салон красоты, онлайн-курсы, доставка еды)",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_business)

@dp.message(BotRequest.waiting_for_business)
async def process_business(message: types.Message, state: FSMContext):
    if await check_timeout(state, message):
        return
    
    await state.update_data(business=message.text)
    await update_last_activity(state)
    
    await message.answer(
        "🎯 <b>Для чего вам нужен бот?</b>\n\n"
        "Выберите основную цель:",
        parse_mode="HTML",
        reply_markup=get_purpose_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_purpose)

@dp.callback_query(BotRequest.waiting_for_purpose, F.data.startswith("purpose_"))
async def process_purpose(callback: types.CallbackQuery, state: FSMContext):
    if await check_timeout(state):
        await callback.message.edit_text("⏰ Сессия истекла. Напишите /start")
        await callback.answer()
        return
    
    purpose_map = {
        "purpose_sales": "🛍 Продажи товаров/услуг",
        "purpose_booking": "📅 Запись клиентов",
        "purpose_support": "💬 Поддержка клиентов",
        "purpose_content": "📚 Рассылка контента",
        "purpose_other": "📝 Другое"
    }
    
    purpose_text = purpose_map.get(callback.data, "Другое")
    await state.update_data(purpose=purpose_text)
    await update_last_activity(state)
    
    await callback.message.edit_text(
        f"Выбрано: <b>{purpose_text}</b>\n\n"
        "📝 <b>Теперь опишите подробнее, что должен уметь бот:</b>\n\n"
        "<i>Например: принимать заказы на доставку, показывать меню с ценами, "
        "принимать оплату онлайн, отправлять уведомления клиентам.</i>",
        parse_mode="HTML"
    )
    await callback.answer()
    await state.set_state(BotRequest.waiting_for_description)

@dp.message(BotRequest.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    if await check_timeout(state, message):
        return
    
    # ИСПРАВЛЕННЫЙ ТЕКСТ - без упоминания "символов"
    if len(message.text.strip()) < 15:
        await message.answer(
            "✏️ <b>Пожалуйста, опишите подробнее.</b>\n\n"
            "Напишите 2-3 предложения о том, как должен работать бот, "
            "для кого он и какие основные действия выполнять.",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(description=message.text)
    await update_last_activity(state)
    
    await message.answer(
        "💰 <b>Какой бюджет на бота вы рассматриваете?</b>\n\n"
        "Выберите подходящий вариант:",
        parse_mode="HTML",
        reply_markup=get_budget_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_budget)

@dp.callback_query(BotRequest.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget(callback: types.CallbackQuery, state: FSMContext):
    if await check_timeout(state):
        await callback.message.edit_text("⏰ Сессия истекла. Напишите /start")
        await callback.answer()
        return
    
    budget_map = {
        "budget_free": "Бесплатно (тест)",
        "budget_1000": "до 1000₽/месяц",
        "budget_3000": "1000-3000₽/месяц",
        "budget_5000": "3000-5000₽/месяц",
        "budget_5000+": "5000₽+/месяц",
        "budget_unknown": "Ещё не решил"
    }
    
    budget_text = budget_map.get(callback.data, "Ещё не решил")
    await state.update_data(budget=budget_text)
    await update_last_activity(state)
    
    user_data = await state.get_data()
    
    # Формируем сводку
    summary = f"""
✅ <b>Отлично! Вот что у нас получилось:</b>

👤 <b>Имя:</b> {user_data.get('name')}
📞 <b>Контакт:</b> {user_data.get('contact')}
🏢 <b>Бизнес:</b> {user_data.get('business')}
🎯 <b>Цель бота:</b> {user_data.get('purpose')}
💰 <b>Бюджет:</b> {user_data.get('budget')}
📝 <b>Описание:</b>
{user_data.get('description')}
"""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="✅ Всё верно, отправить заявку",
        callback_data="confirm_request"
    ))
    keyboard.add(InlineKeyboardButton(
        text="✏️ Исправить данные",
        callback_data="edit_request"
    ))
    
    await callback.message.edit_text(
        summary,
        parse_mode="HTML",
        reply_markup=keyboard.as_markup()
    )
    await callback.answer()
    await state.set_state(BotRequest.waiting_for_confirmation)

@dp.callback_query(BotRequest.waiting_for_confirmation, F.data == "confirm_request")
async def confirm_request(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    request_id = f"REQ-{datetime.now().strftime('%Y%m%d')}-{callback.from_user.id}"
    
    # Отправляем уведомление администратору
    admin_notified = await send_request_to_admin(user_data, callback.from_user.id, request_id)
    
    # Сохраняем в локальный файл
    file_saved = save_to_log_file(user_data, request_id)
    
    if admin_notified or file_saved:
        success_message = f"""
✅ <b>Заявка #{request_id} отправлена!</b>

Спасибо за обращение! Наш менеджер свяжется с вами в течение 15 минут для уточнения деталей.

💡 <b>Что дальше?</b>
1. Мы анализируем ваши потребности
2. Предлагаем оптимальное решение
3. Создаём прототип бота
4. Вы тестируете и вносите правки
5. Запускаем в работу!

📞 <b>По вопросам:</b> @botforge_support
"""
        await callback.message.edit_text(success_message, parse_mode="HTML")
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при отправке заявки. "
            "Пожалуйста, напишите нам напрямую: @botforge_support",
            parse_mode="HTML"
        )
    
    await callback.answer()
    await state.clear()

# ==================== ИСПРАВЛЕННЫЙ ОБРАБОТЧИК РЕДАКТИРОВАНИЯ ====================
@dp.callback_query(BotRequest.waiting_for_confirmation, F.data == "edit_request")
async def edit_request(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardBuilder()
    buttons = [
        ("👤 Изменить имя", "edit_name"),
        ("📞 Изменить контакт", "edit_contact"),
        ("🏢 Изменить бизнес", "edit_business"),
        ("🎯 Изменить цель", "edit_purpose"),
        ("📝 Изменить описание", "edit_description"),
        ("💰 Изменить бюджет", "edit_budget"),
        ("✅ Всё верно", "confirm_request")
    ]
    
    for text, data in buttons:
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    
    await callback.message.edit_text(
        "✏️ <b>Что хотите изменить?</b>",
        parse_mode="HTML",
        reply_markup=keyboard.adjust(2).as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def handle_edit(callback: types.CallbackQuery, state: FSMContext):
    """ИСПРАВЛЕННАЯ ФУНКЦИЯ - теперь корректно меняет состояния"""
    edit_type = callback.data.replace("edit_", "")
    
    # Снимаем "часики" с кнопки
    await callback.answer()
    
    if edit_type == "name":
        await callback.message.answer("Как вас зовут?", reply_markup=get_cancel_keyboard())
        await state.set_state(BotRequest.waiting_for_name)
    elif edit_type == "contact":
        await callback.message.answer("Как с вами связаться?", reply_markup=get_cancel_keyboard())
        await state.set_state(BotRequest.waiting_for_contact)
    elif edit_type == "business":
        await callback.message.answer("Чем занимается ваш бизнес?", reply_markup=get_cancel_keyboard())
        await state.set_state(BotRequest.waiting_for_business)
    elif edit_type == "purpose":
        await callback.message.answer(
            "Для чего вам нужен бот?",
            reply_markup=get_purpose_keyboard()
        )
        await state.set_state(BotRequest.waiting_for_purpose)
    elif edit_type == "description":
        await callback.message.answer("Опишите подробнее, что должен уметь бот:")
        await state.set_state(BotRequest.waiting_for_description)
    elif edit_type == "budget":
        await callback.message.answer(
            "Какой бюджет на бота?",
            reply_markup=get_budget_keyboard()
        )
        await state.set_state(BotRequest.waiting_for_budget)

# ==================== ОБРАБОТЧИК ПРИНЯТИЯ ЗАЯВКИ ====================
@dp.callback_query(F.data.startswith("accept_"))
async def handle_admin_accept(callback: types.CallbackQuery):
    user_id = callback.data.replace("accept_", "")
    
    try:
        # Отправляем уведомление клиенту
        await bot.send_message(
            chat_id=int(user_id),
            text="🎉 <b>Отличные новости!</b>\n\n"
                 "Ваша заявка принята в работу! Наш специалист свяжется с вами "
                 "в ближайшее время для уточнения деталей.\n\n"
                 "⏰ <b>Ожидайте связи в течение часа.</b>",
            parse_mode="HTML"
        )
        
        # Обновляем сообщение админу
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Заявка принята в работу</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Клиент уведомлен")
        
    except Exception as e:
        await callback.answer("❌ Ошибка при уведомлении клиента")
        logger.error(f"Ошибка уведомления клиента: {e}")

# ==================== ОБРАБОТЧИК ЛЮБЫХ ДРУГИХ СООБЩЕНИЙ ====================
@dp.message()
async def handle_other_messages(message: types.Message):
    if message.text and len(message.text) > 3:
        await message.answer(
            "🤖 Для создания бота напишите /start\n"
            "❓ Помощь - /help"
        )

# ==================== ЗАПУСК БОТА ====================
async def main():
    logger.info("🚀 Бот запускается... (без Google Sheets)")
    
    # Удаляем вебхук если был
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг в фоновой задаче
    dp.run_polling_task = asyncio.create_task(dp.start_polling(bot))
    
    # Создаем событие для ожидания завершения
    shutdown_event = asyncio.Event()
    
    # Обработка сигналов завершения
    loop = asyncio.get_event_loop()
    for signal in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signal, lambda s=signal: asyncio.create_task(shutdown(s)))
    
    async def shutdown(sig=None):
        if sig:
            logger.info(f"🛑 Получен сигнал {sig.name}")
        logger.info("🛑 Останавливаю бота...")
        
        # Отменяем задачу поллинга
        if dp.run_polling_task:
            dp.run_polling_task.cancel()
            try:
                await dp.run_polling_task
            except asyncio.CancelledError:
                pass
        
        # Останавливаем диспетчер
        await dp.stop_polling()
        
        # Закрываем сессию бота
        await bot.session.close()
        
        logger.info("✅ Бот остановлен корректно")
        shutdown_event.set()
    
    # Ждем события завершения
    await shutdown_event.wait()

if __name__ == "__main__":
    import signal
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен вручную")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        exit(1)

