import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Получение токена из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не установлен!")
    exit(1)

if not ADMIN_CHAT_ID:
    logger.error("ADMIN_CHAT_ID не установлен!")
    exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для опроса
class BotRequest(StatesGroup):
    waiting_for_name = State()
    waiting_for_contact = State()
    waiting_for_business = State()
    waiting_for_purpose = State()
    waiting_for_description = State()
    waiting_for_budget = State()
    waiting_for_confirmation = State()

# Клавиатура для выбора цели бота
def get_purpose_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="🛍 Продажи", 
        callback_data="purpose_sales"
    ))
    keyboard.add(InlineKeyboardButton(
        text="📅 Запись", 
        callback_data="purpose_booking"
    ))
    keyboard.add(InlineKeyboardButton(
        text="💬 Поддержка", 
        callback_data="purpose_support"
    ))
    keyboard.add(InlineKeyboardButton(
        text="📚 Контент", 
        callback_data="purpose_content"
    ))
    keyboard.add(InlineKeyboardButton(
        text="📝 Другое", 
        callback_data="purpose_other"
    ))
    return keyboard.adjust(2).as_markup()

# Клавиатура для выбора бюджета
def get_budget_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(
        text="Бесплатно (тест)", 
        callback_data="budget_free"
    ))
    keyboard.add(InlineKeyboardButton(
        text="до 1000₽/мес", 
        callback_data="budget_1000"
    ))
    keyboard.add(InlineKeyboardButton(
        text="1000-3000₽/мес", 
        callback_data="budget_3000"
    ))
    keyboard.add(InlineKeyboardButton(
        text="3000-5000₽/мес", 
        callback_data="budget_5000"
    ))
    keyboard.add(InlineKeyboardButton(
        text="5000₽+/мес", 
        callback_data="budget_5000+"
    ))
    keyboard.add(InlineKeyboardButton(
        text="Ещё не решил", 
        callback_data="budget_unknown"
    ))
    return keyboard.adjust(2).as_markup()

# Отправка заявки админу
async def send_request_to_admin(user_data: Dict[str, Any], user_id: int):
    request_id = f"REQ-{datetime.now().strftime('%Y%m%d')}-{user_id}"
    
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
        return request_id
    except Exception as e:
        logger.error(f"Ошибка отправки заявки админу: {e}")
        return None

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    welcome_text = """
🤖 <b>Привет! Я помогу создать Telegram-бота для вашего бизнеса</b>

За 5 минут мы определим:
• Какой бот вам нужен
• Какие функции необходимы
• Сколько это будет стоить
• Как быстро можно запустить

<b>Поехали! Как вас зовут?</b>
"""
    
    await message.answer(welcome_text, parse_mode="HTML")
    await state.set_state(BotRequest.waiting_for_name)

# Обработка имени
@dp.message(BotRequest.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    await message.answer(
        f"Отлично, {message.text}! 📞\n"
        "Как с вами связаться? (Telegram @username, номер телефона или email)"
    )
    await state.set_state(BotRequest.waiting_for_contact)

# Обработка контакта
@dp.message(BotRequest.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    
    await message.answer(
        "🏢 Чем занимается ваш бизнес? (Например: салон красоты, онлайн-курсы, доставка еды)"
    )
    await state.set_state(BotRequest.waiting_for_business)

# Обработка бизнеса
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

# Обработка выбора цели через inline кнопки
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
        "Например:\n"
        "• Принимать заказы на доставку\n"
        "• Показывать меню с ценами\n"
        "• Принимать оплату онлайн\n"
        "• Отправлять уведомления клиентам",
        parse_mode="HTML"
    )
    
    await callback.answer()
    await state.set_state(BotRequest.waiting_for_description)

# Обработка описания
@dp.message(BotRequest.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    if len(message.text) < 10:
        await message.answer("Пожалуйста, опишите подробнее (минимум 10 символов)")
        return
    
    await state.update_data(description=message.text)
    
    await message.answer(
        "💰 <b>Какой бюджет на бота вы рассматриваете?</b>\n\n"
        "Выберите подходящий вариант:",
        parse_mode="HTML",
        reply_markup=get_budget_keyboard()
    )
    await state.set_state(BotRequest.waiting_for_budget)

# Обработка бюджета через inline кнопки
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
    
    # Получаем все данные
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

# Подтверждение заявки
@dp.callback_query(BotRequest.waiting_for_confirmation, F.data == "confirm_request")
async def confirm_request(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    
    # Отправляем админу
    request_id = await send_request_to_admin(user_data, callback.from_user.id)
    
    if request_id:
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
        
        await callback.message.edit_text(
            success_message,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при отправке заявки. "
            "Пожалуйста, напишите нам напрямую: @botforge_support",
            parse_mode="HTML"
        )
    
    await callback.answer()
    await state.clear()

# Кнопка принятия заявки админом
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

# Обработка команды /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
<b>🤖 BotForge - создание Telegram-ботов</b>

<b>Команды:</b>
/start - начать создание бота
/help - показать это сообщение

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

# Обработка любых других сообщений
@dp.message()
async def handle_other_messages(message: types.Message):
    if message.text and len(message.text) > 3:
        await message.answer(
            "🤖 Для создания бота напишите /start\n"
            "❓ Помощь - /help"
        )

# Запуск бота
async def main():
    logger.info("Бот запускается...")
    
    # Удаляем вебхук если был
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
