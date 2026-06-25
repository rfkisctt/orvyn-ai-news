import logging
import sys
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from config import (
    DISCORD_TOKEN, RSS_FEEDS, CHECK_INTERVAL_MINUTES, MAX_ITEMS_PER_POST, EMBED_COLOR,
    get_image_url, is_model_news, is_today_wib, get_news_channel_id, set_news_channel_id,
    detect_category, detect_badge_type, MODEL_KEYWORDS, MODEL_IMAGES, PROVIDER_URLS
)
from services.news_fetcher import NewsFetcher
from services.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ai-news-bot")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Discord bot accounts only get one activity slot (unlike user accounts with
# custom status + game simultaneously). Workaround: auto-rotate every
# STATUS_ROTATE_SECONDS to show both the command bubble and stats display,
# with their native formatting preserved (custom for bubble, watching for stats).
STATUS_TEXT = "/help & /setchannel"
STATUS_ROTATE_SECONDS = 20


def build_command_bubble() -> discord.CustomActivity:
    return discord.CustomActivity(name=STATUS_TEXT)


def build_watching_activity(guild_count: int, member_count: int) -> discord.Activity:
    server_word = "server" if guild_count == 1 else "servers"
    user_word = "user" if member_count == 1 else "users"
    return discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{guild_count} {server_word} | {member_count} {user_word}",
    )


class AINewsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.fetcher = NewsFetcher()
        self.storage = Storage()
        self._posted_count = 0
        self._status_phase = 0
        self.last_check_at: Optional[datetime] = None

    async def setup_hook(self):
        # Start background tasks
        self.check_news.start()
        self.rotate_status.start()
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands (/)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def check_news(self):
        channel_id = get_news_channel_id()
        if not channel_id:
            return

        channel = self.get_channel(channel_id)
        if not channel:
            return

        items = await self.fetcher.fetch_all_feeds(RSS_FEEDS)
        self.last_check_at = datetime.now(timezone.utc)
        if not items:
            return

        if self.storage.is_first_run:
            self.storage.mark_many_posted([i.link for i in items])
            self.storage.is_first_run = False
            self.storage.save()
            return

        filtered_items = []
        for item in items:
            text = f"{item.title} {item.description}"
            if is_model_news(text) and is_today_wib(item.published_parsed):
                if not self.storage.is_posted(item.link):
                    filtered_items.append(item)

        if not filtered_items:
            return

        for item in filtered_items[:MAX_ITEMS_PER_POST]:
            try:
                embed, logo_path = self.create_embed(item)
                if logo_path:
                    file = discord.File(logo_path, filename=os.path.basename(logo_path))
                    await channel.send(embed=embed, file=file)
                else:
                    await channel.send(embed=embed)
                self.storage.mark_posted(item.link)
                self._posted_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to send news item {item.link}: {e}")

        for item in filtered_items[MAX_ITEMS_PER_POST:]:
            self.storage.mark_posted(item.link)
        self.storage.save()

    @check_news.before_loop
    async def before_check_news(self):
        await self.wait_until_ready()

    @tasks.loop(seconds=STATUS_ROTATE_SECONDS)
    async def rotate_status(self):
        if self._status_phase == 0:
            activity = build_command_bubble()
        else:
            guild_count = len(self.guilds)
            member_count = sum(g.member_count or 0 for g in self.guilds)
            activity = build_watching_activity(guild_count, member_count)
        try:
            await self.change_presence(activity=activity, status=discord.Status.online)
        except Exception as e:
            logger.error(f"Failed to update presence: {e}")
        self._status_phase = 1 - self._status_phase

    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.wait_until_ready()

    async def close(self):
        await self.fetcher.close()
        await super().close()

    def create_embed(self, item):
        # Extract model name from title
        model_name = self._extract_model_name(item.title)
        
        # Get provider URL
        provider_url = self._get_provider_url(f"{item.title} {item.description}")
        
        # Create embed with model name as title
        embed = discord.Embed(
            title=f"{item.badge_type}: {model_name}",
            description=item.title[:300],  # Shorten to avoid too long title
            url=provider_url or item.link,
            color=EMBED_COLOR
        )
        
        # Add description field
        desc = item.description[:400] if item.description else "No description available."
        embed.add_field(name="Details", value=desc, inline=False)
        
        # Add metadata
        embed.add_field(name="Provider", value=item.source, inline=True)
        embed.add_field(name="Category", value=item.category, inline=True)
        
        if item.published:
            embed.add_field(name="Published", value=item.published[:100], inline=True)
        
        # Prefer a local public logo when available
        local_logo_path = self._get_provider_logo_path(f"{item.title} {item.description}")
        if local_logo_path:
            embed.set_thumbnail(url=f"attachment://{os.path.basename(local_logo_path)}")
            embed.timestamp = discord.utils.utcnow()
            return embed, local_logo_path
        
        # Use bot avatar if no local file is available
        if self.user and self.user.display_avatar:
            embed.set_thumbnail(url=str(self.user.display_avatar.url))
            embed.timestamp = discord.utils.utcnow()
            return embed, None
        
        logo_path = self._get_provider_logo(f"{item.title} {item.description}")
        if logo_path and os.path.exists(logo_path):
            embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")
            embed.timestamp = discord.utils.utcnow()
            return embed, logo_path
        
        embed.timestamp = discord.utils.utcnow()
        return embed, None
    
    def _get_provider_logo_path(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        public_dir = os.path.join(os.path.dirname(__file__), "public")
        for keyword in MODEL_IMAGES:
            if keyword in text_lower:
                filename = keyword.replace(" ", "_").replace("/", "_").replace(".", "_").replace("·", "_") + ".png"
                candidate = os.path.join(public_dir, filename)
                if os.path.exists(candidate):
                    return candidate
        return None
    
    def _extract_model_name(self, title: str) -> str:
        """Extract model name and version from title."""
        title_lower = title.lower()
        
        # Try to find model keyword and extract surrounding text
        for keyword in MODEL_KEYWORDS:
            if keyword in title_lower:
                # Find the position of keyword
                idx = title_lower.find(keyword)
                # Extract a chunk around the keyword (up to 50 chars forward)
                chunk = title[idx:min(idx + 50, len(title))].strip()
                # Take first "word" or "word version" (e.g., "GPT-4", "Claude 3.5 Sonnet")
                words = chunk.split()
                if len(words) >= 2 and (words[1][0].isdigit() or words[1].lower() in ['v', 'version']):
                    return f"{words[0]} {words[1]}".title()
                elif len(words) >= 1:
                    return words[0].title()
        
        # Fallback: take first 40 chars of title
        return title[:40].strip()
    
    def _get_provider_logo(self, text: str) -> str:
        """Get provider logo URL or local default logo path."""
        text_lower = text.lower()
        for keyword, url in MODEL_IMAGES.items():
            if keyword in text_lower:
                return url
        return os.path.join(os.path.dirname(__file__), "public", "return_logo.png")
    
    def _get_provider_url(self, text: str) -> str:
        """Get provider website URL."""
        text_lower = text.lower()
        for keyword, url in PROVIDER_URLS.items():
            if keyword in text_lower:
                return url
        return None


bot = AINewsBot()


@bot.event
async def on_ready():
    logger.info("=" * 60)
    logger.info(f"Bot logged in as: {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")
    logger.info("=" * 60)
    logger.info("Bot is fully ready and auto-posting is active!")


@bot.event
async def on_guild_join(guild):
    logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")


@bot.event
async def on_guild_remove(guild):
    logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")


# --- Commands ---
@bot.tree.command(name="setchannel", description="Set channel for auto-posting AI model news")
@app_commands.default_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_news_channel_id(channel.id)
    embed = discord.Embed(
        title="Channel Set",
        description=f"AI Model news will be auto-posted in {channel.mention}",
        color=EMBED_COLOR,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Show the bot's current config and stats")
async def status(interaction: discord.Interaction):
    channel_id = get_news_channel_id()
    channel_text = f"<#{channel_id}>" if channel_id else "Not set yet — use `/setchannel`"
    stats = bot.storage.get_stats()
    last_check = (
        discord.utils.format_dt(bot.last_check_at, style="R")
        if bot.last_check_at else "Not yet"
    )

    embed = discord.Embed(title="Bot Status", color=EMBED_COLOR)
    embed.add_field(name="News Channel", value=channel_text, inline=False)
    embed.add_field(name="Check Interval", value=f"Every {CHECK_INTERVAL_MINUTES} min", inline=True)
    embed.add_field(name="Last Check", value=last_check, inline=True)
    embed.add_field(name="Total Posted (all-time)", value=str(stats["total_posted"]), inline=True)
    embed.add_field(name="Posted This Session", value=str(bot._posted_count), inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="test", description="Test news embed format with sample data")
async def test_command(interaction: discord.Interaction):
    from services.news_fetcher import NewsItem
    
    # Create sample news item for testing
    sample_item = NewsItem(
        title=f"{bot.user.name}",
        link="https://claude.ai",
        description="New model release with enhanced reasoning capabilities, improved code generation, and better multi-modal understanding. Supports longer context windows and faster processing.",
        source=f"{bot.user.name} Blog",
        published=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        published_parsed=None,
        category="Launch",
        badge_emoji="🚀",
        badge_type="Model Release"
    )
    
    # Create embed using the bot's create_embed method
    embed, logo_path = bot.create_embed(sample_item)
    
    # Use explicit public return logo for test embeds when available
    public_logo = os.path.join(os.path.dirname(__file__), "public", "return_logo.png")
    if os.path.exists(public_logo):
        embed.set_thumbnail(url="attachment://return_logo.png")
        await interaction.response.send_message(embed=embed, file=discord.File(public_logo, filename="return_logo.png"))
    elif logo_path:
        file = discord.File(logo_path, filename=os.path.basename(logo_path))
        await interaction.response.send_message(embed=embed, file=file)
    else:
        await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="Show what this bot does and its commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Orvyn",
        description="Auto-posts news whenever an AI model gets launched or updated.",
        color=EMBED_COLOR,
    )
    embed.add_field(name="/setchannel", value="Set the channel for auto-posted AI news (admin only)", inline=False)
    embed.add_field(name="/status", value="Show the bot's current config and stats", inline=False)
    embed.add_field(name="/test", value="Test news embed format with sample data", inline=False)
    embed.add_field(name="/help", value="Show this message", inline=False)
    await interaction.response.send_message(embed=embed)


def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found! Set it in .env file.")
        sys.exit(1)
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    except discord.LoginFailure:
        logger.error("Invalid Discord token!")
        sys.exit(1)


if __name__ == "__main__":
    main()