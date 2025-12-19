import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any
from contextlib import asynccontextmanager

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

# ==================== СОХРАНЕНИЕ В ФАЙЛ ====================
LOG_FILE = "requests.log"

# Очередь для асинхронной записи логов
log_queue = asyncio.Queue()

async def log_worker():
    """Фоновая задача для записи логов в файл"""
    while True:
        try:
            log_data = await log_queue.get()
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(log_data + "\n")
                    f.flush()
                logger.info(f"✅ Запись в лог сохранена")
            except Exception as e:
                logger.error(f"❌ Ошибка записи в файл: {e}")
            finally:
                log_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в лог-воркере: {e}")

async def save_to_log(user_data: Dict[str, Any], request_id: str):
    """Добавляет заявку в очередь для записи в текстовый файл."""
    try:
        log_entry = f"""
{'='*60}
Заявка #{request_id} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
👤 Имя: {user_data.get('name', '')}
📞 Контакт: {user_data.get('contact', '')}
🏢 Бизнес: {user_data.get('business', '')}
🎯 Цель: {user_data.get('purpose', '')}
💰 Бюджет: {user_data.get('budget', '')}
📝 Описание: {user_data.get('description', '')}
{'='*60}
"""
        await log_queue.put(log_entry)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления в очередь логов: {e}")
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
"""
    
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode="HTML"
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
    await message.answer(welcome_text, parse_mode="HTML")
    await state.set_state(BotRequest.waiting_for_name)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
<b>🤖 BotForge - создание Telegram-ботов</b>

<b>Команды:</b>
/start - начать создание бота
/help - показать это сообщение
/cancel - отменить текущий опрос

<b>Контакты:</b>
Поддержка: @botforge_support
"""
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Опрос отменен. Напишите /start для начала.")

# ==================== ОБРАБОТЧИКИ ДИАЛОГА ====================
@dp.message(BotRequest.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        f"Отлично, {message.text}! 📞\n"
        "Как с вами связаться? (Telegram @username, номер телефона или email)"
    )
    await state.set_state(BotRequest.waiting_for_contact)

@dp.message(BotRequest.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await message.answer(
        "🏢 Чем занимается ваш бизнес? (Например: салон красоты, онлайн-курсы, доставка еды)"
    )
    await state.set_state(BotRequest.waiting_for_business)

@dp.message(BotRequest.waiting_for_business)
async def process_business(message: types.Message, state: FSMContext):
    await state.update_data(business=message.text)
    await message.answer(
        "🎯 <b>Для чего вам нужен бот?</b>\n\n"
        "Выберите основную цель:",
        parse_mode="HTML",
        reply_markup=get_purpose_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_purpose)

@dp.callback_query(BotRequest.waiting_for_purpose, F.data.startswith("purpose_"))
async def process_purpose(callback: types.CallbackQuery, state: FSMContext):
    purpose_map = {
        "purpose_sales": "🛍 Продажи товаров/услуг",
        "purpose_booking": "📅 Запись клиентов",
        "purpose_support": "💬 Поддержка клиентов",
        "purpose_content": "📚 Рассылка контента",
        "purpose_other": "📝 Другое"
    }
    purpose_text = purpose_map.get(callback.data, "Другое")
    await state.update_data(purpose=purpose_text)
    
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
    if len(message.text.strip()) < 15:
        await message.answer(
            "✏️ <b>Пожалуйста, опишите подробнее.</b>\n\n"
            "Напишите 2-3 предложения о том, как должен работать бот.",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(description=message.text)
    
    await message.answer(
        "💰 <b>Какой бюджет на бота вы рассматриваете?</b>\n\n"
        "Выберите подходящий вариант:",
        parse_mode="HTML",
        reply_markup=get_budget_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_budget)

@dp.callback_query(BotRequest.waiting_for_budget, F.data.startswith("budget_"))
async def process_budget(callback: types.CallbackQuery, state: FSMContext):
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
    
    user_data = await state.get_data()
    request_id = f"REQ-{datetime.now().strftime('%Y%m%d')}-{callback.from_user.id}"
    
    # Отправляем админу и сохраняем в файл (через очередь)
    await send_request_to_admin(user_data, callback.from_user.id, request_id)
    await save_to_log(user_data, request_id)
    
    success_message = f"""
✅ <b>Заявка #{request_id} отправлена!</b>

Спасибо за обращение! Наш менеджер свяжется с вами в течение 15 минут.

💡 <b>Что дальше?</b>
1. Мы анализируем ваши потребности
2. Предлагаем оптимальное решение
3. Создаём прототип бота
4. Вы тестируете и вносите правки
5. Запускаем в работу!

📞 <b>По вопросам:</b> @botforge_support
"""
    await callback.message.edit_text(success_message, parse_mode="HTML")
    await callback.answer()
    await state.clear()

# ==================== LIFESPAN УПРАВЛЕНИЕ ====================
@asynccontextmanager
async def lifespan():
    """Управление жизненным циклом бота"""
    log_task = None
    try:
        # Startup
        logger.info("🚀 Бот запускается...")
        
        # Удаляем старый вебхук
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Создаем лог-файл если его нет
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"Лог заявок BotForge. Начало: {datetime.now()}\n{'='*60}\n")
        
        # Запускаем фоновую задачу для записи логов
        log_task = asyncio.create_task(log_worker())
        
        yield
    finally:
        # Shutdown
        logger.info("🛑 Бот завершает работу...")
        
        # Отменяем фоновую задачу логов
        if log_task:
            log_task.cancel()
            try:
                await log_task
            except asyncio.CancelledError:
                pass
        
        # Ждем завершения обработки очереди логов
        await log_queue.join()
        
        # Закрываем сессию бота
        await bot.session.close()
        
        logger.info("✅ Бот корректно остановлен")

# ==================== ЗАПУСК БОТА ====================
async def main():
    """Основная функция запуска бота"""
    try:
        # Используем lifespan для управления состоянием
        async with lifespan():
            # Запускаем поллинг
            await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("Приложение завершено")

if __name__ == "__main__":
    asyncio.run(main())
