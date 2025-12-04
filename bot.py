import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    init_db, add_user, add_news, get_unsent_news, 
    mark_news_as_sent, get_all_users, get_user_frequency
)
from parser import fetch_news

# Загружаем токен
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не найден в .env файле!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# FSM для управления состояниями
class NewsState(StatesGroup):
    waiting_for_frequency = State()

# ==================== HANDLERS ====================

@dp.message(Command('start'))
async def start_handler(message: types.Message, state: FSMContext):
    """Обработчик /start"""
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Каждые 10 минут", callback_data="freq_10m")],
        [InlineKeyboardButton(text="⏱ Каждые полчаса", callback_data="freq_30m")],
        [InlineKeyboardButton(text="⏲ Каждый час", callback_data="freq_1h")],
        [InlineKeyboardButton(text="📅 Каждый день", callback_data="freq_1d")],
    ])
    
    await message.answer(
        "👋 Привет! Я отслеживаю все актуальные новости об искусственном интеллекте в России.\n\n"
        "🔔 Как часто тебе отправлять сводку новостей?",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("freq_"))
async def frequency_handler(callback_query: types.CallbackQuery):
    """Обработчик выбора частоты"""
    user_id = callback_query.from_user.id
    frequency_map = {
        "freq_10m": "10m",
        "freq_30m": "30m",
        "freq_1h": "1h",
        "freq_1d": "1d"
    }
    
    frequency = frequency_map[callback_query.data]
    await add_user(user_id, frequency)
    
    # Сразу отправляем первые новости
    await send_news_to_user(user_id)
    
    await callback_query.answer(f"✅ Частота установлена: {callback_query.data.replace('freq_', '')}")
    await callback_query.message.edit_text(
        f"🎉 Готово! Я буду отправлять тебе новости об ИИ в России.\n\n"
        f"Следующая отправка будет согласно выбранному расписанию."
    )

@dp.message(Command('help'))
async def help_handler(message: types.Message):
    """Помощь"""
    await message.answer(
        "📖 Справка:\n\n"
        "/start — начать и выбрать частоту новостей\n"
        "/help — эта справка\n"
        "/now — получить свежие новости прямо сейчас\n\n"
        "🤖 Бот автоматически отправляет новости об ИИ в России в зависимости от твоего выбора."
    )

@dp.message(Command('now'))
async def now_handler(message: types.Message):
    """Получить новости прямо сейчас"""
    await send_news_to_user(message.from_user.id)
    await message.answer("✅ Отправил свежие новости!")

# ==================== ФУНКЦИИ ====================

async def send_news_to_user(user_id: int):
    """Отправить новости пользователю"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Получаем новости из парсера
        print(f"📡 Получаю новости за {today}...")
        news_list = await fetch_news(today)
        
        if not news_list:
            await bot.send_message(user_id, "😔 Сегодня новостей об ИИ в России не найдено.")
            return
        
        # Добавляем в БД
        for news in news_list:
            await add_news(
                title=news['title'],
                summary=news['summary'],
                url=news['url'],
                source=news['source'],
                date=today
            )
        
        # Получаем новости, которые ещё не отправляли
        unsent = await get_unsent_news(user_id, today)
        
        if not unsent:
            await bot.send_message(user_id, "✅ Все новости уже отправлены!")
            return
        
        # Отправляем новости
        message_text = f"🤖 Новости об ИИ в России ({today}):\n\n"
        
        for news_id, title, summary, url, source in unsent[:5]:  # Максимум 5 новостей за раз
            message_text += (
                f"📰 <b>{title}</b>\n"
                f"📝 {summary}\n"
                f"🔗 <a href='{url}'>Читать на {source}</a>\n\n"
            )
            
            # Отмечаем как отправленную
            await mark_news_as_sent(user_id, news_id)
        
        await bot.send_message(user_id, message_text, parse_mode="HTML")
        
    except Exception as e:
        print(f"❌ Ошибка при отправке новостей пользователю {user_id}: {e}")
        await bot.send_message(user_id, "❌ Ошибка при получении новостей. Попробуй позже.")

async def scheduled_news_sender():
    """Функция для периодической отправки новостей"""
    while True:
        try:
            users = await get_all_users()
            
            for user_id in users:
                frequency = await get_user_frequency(user_id)
                
                # Определяем интервал в секундах
                intervals = {
                    "10m": 600,
                    "30m": 1800,
                    "1h": 3600,
                    "1d": 86400
                }
                
                interval = intervals.get(frequency, 3600)
                
                # Отправляем новости
                await send_news_to_user(user_id)
            
            # Ждём перед следующей проверкой (проверяем каждые 10 минут)
            await asyncio.sleep(600)
            
        except Exception as e:
            print(f"❌ Ошибка в scheduled_news_sender: {e}")
            await asyncio.sleep(60)

async def main():
    """Запуск бота"""
    print("🚀 Инициализирую БД...")
    await init_db()
    
    print("🤖 Бот запущен и готов получать сообщения!")
    print("💡 Нажми /start в Telegram чтобы начать")
    
    # Запускаем отправку новостей в фоне
    asyncio.create_task(scheduled_news_sender())
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
