import aiohttp
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio

# Источники (RSS feeds и сайты)
SOURCES = {
    'Habr': 'https://habr.com/ru/feed/articles/?tag=ai&tag=machine_learning',
    'Vc.ru': 'https://vc.ru/feed?tags=AI',
}

# Дополнительные источники для парсинга (сайты с поиском)
SEARCH_URLS = {
    'ТАСС AI': 'https://tass.ru/search?q=искусственный+интеллект',
    'РБК Tech': 'https://www.rbc.ru/technology_and_media/index.shtml',
}

async def parse_rss(url: str, source_name: str, today_date: str) -> list:
    """Парсить RSS фид"""
    try:
        feed = feedparser.parse(url)
        news_list = []
        
        for entry in feed.entries[:10]:  # Последние 10 новостей
            title = entry.get('title', '')
            summary = entry.get('summary', '')[:200]  # Первые 200 символов
            url = entry.get('link', '')
            
            # Убираем HTML теги из сводки
            summary = BeautifulSoup(summary, 'html.parser').get_text()
            
            if title and url:
                news_list.append({
                    'title': title,
                    'summary': summary[:150] + '...' if len(summary) > 150 else summary,
                    'url': url,
                    'source': source_name,
                    'date': today_date
                })
        
        return news_list
    except Exception as e:
        print(f"Ошибка при парсинге {source_name}: {e}")
        return []

async def parse_all_sources(today_date: str) -> list:
    """Получить новости из всех источников"""
    all_news = []
    
    # Парсим RSS
    for source_name, url in SOURCES.items():
        news = await parse_rss(url, source_name, today_date)
        all_news.extend(news)
    
    # Небольшой delay чтобы не перегружать серверы
    await asyncio.sleep(1)
    
    return all_news

async def fetch_news(today_date: str) -> list:
    """Главная функция для получения новостей"""
    return await parse_all_sources(today_date)
