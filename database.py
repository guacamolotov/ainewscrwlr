import aiosqlite
import os
from datetime import datetime

DB_NAME = 'news.db'

async def init_db():
    """Инициализация БД"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                frequency TEXT DEFAULT '1h',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                summary TEXT,
                url TEXT UNIQUE,
                source TEXT,
                date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS sent_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                news_id INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(news_id) REFERENCES news(id)
            )
        ''')
        
        await db.commit()

async def add_user(user_id: int, frequency: str):
    """Добавить/обновить пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT OR REPLACE INTO users (user_id, frequency) VALUES (?, ?)',
            (user_id, frequency)
        )
        await db.commit()

async def get_user_frequency(user_id: int) -> str:
    """Получить частоту отправки"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT frequency FROM users WHERE user_id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else '1h'

async def add_news(title: str, summary: str, url: str, source: str, date: str):
    """Добавить новость (если её еще нет)"""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                'INSERT INTO news (title, summary, url, source, date) VALUES (?, ?, ?, ?, ?)',
                (title, summary, url, source, date)
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False  # Новость уже есть

async def get_unsent_news(user_id: int, today_date: str):
    """Получить новости, которые ещё не отправляли этому пользователю за сегодня"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            SELECT n.id, n.title, n.summary, n.url, n.source
            FROM news n
            LEFT JOIN sent_news s ON n.id = s.news_id AND s.user_id = ?
            WHERE n.date = ? AND s.id IS NULL
            ORDER BY n.created_at DESC
        ''', (user_id, today_date))
        return await cursor.fetchall()

async def mark_news_as_sent(user_id: int, news_id: int):
    """Отметить новость как отправленную"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            'INSERT INTO sent_news (user_id, news_id) VALUES (?, ?)',
            (user_id, news_id)
        )
        await db.commit()

async def get_all_users():
    """Получить всех пользователей"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('SELECT user_id FROM users')
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
