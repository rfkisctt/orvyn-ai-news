import asyncio
import logging
import ssl
from typing import Dict, List, Optional

import aiohttp
import certifi
import feedparser
from bs4 import BeautifulSoup

from config import detect_category, detect_badge_type

logger = logging.getLogger(__name__)


class NewsItem:
    def __init__(self, title, link, description, source, published="", published_parsed=None, categories=None, category="News", badge_emoji="📰", badge_type="AI NEWS"):
        self.title = title
        self.link = link
        self.description = description
        self.source = source
        self.published = published
        self.published_parsed = published_parsed
        self.categories = categories or []
        self.category = category
        self.badge_emoji = badge_emoji
        self.badge_type = badge_type

    def __eq__(self, other):
        return isinstance(other, NewsItem) and self.link == other.link

    def __hash__(self):
        return hash(self.link)

    def __repr__(self):
        return f"NewsItem(title={self.title[:50]!r}, source={self.source!r})"


class NewsFetcher:
    def __init__(self):
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            # Use certifi's CA bundle instead of OS cert store.
            # Fixes SSLCertVerificationError on Windows and environments
            # where Python doesn't connect to the system CA store.
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "Orvyn-AI-News-Bot/1.0"},
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_feed(self, source_name, url):
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    return []
                content = await response.text()
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, content)
            if not feed.entries:
                return []
            items = []
            for entry in feed.entries:
                title = entry.get("title", "No title").strip()
                link = entry.get("link", "").strip()
                if not link:
                    continue
                description = entry.get("summary", entry.get("description", ""))
                if description:
                    try:
                        soup = BeautifulSoup(description, "html.parser")
                        description = soup.get_text(separator=" ").strip()
                    except Exception:
                        pass
                    if len(description) > 300:
                        description = description[:297] + "..."
                published = entry.get("published", entry.get("updated", ""))
                published_parsed = entry.get("published_parsed", None)
                
                # Detect category and badge type from title + description
                text_content = f"{title} {description}"
                category = detect_category(text_content)
                badge_emoji, badge_type = detect_badge_type(text_content)
                
                items.append(NewsItem(
                    title=title, link=link, description=description, source=source_name,
                    published=published, published_parsed=published_parsed,
                    category=category, badge_emoji=badge_emoji, badge_type=badge_type
                ))
            return items
        except Exception as e:
            logger.error(f"  Error fetching '{source_name}': {e}")
            return []

    async def fetch_all_feeds(self, feeds):
        if not feeds:
            return []
        tasks = [self.fetch_feed(name, url) for name, url in feeds.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
        seen = set()
        unique = []
        for item in all_items:
            if item.link not in seen:
                seen.add(item.link)
                unique.append(item)
        return unique
