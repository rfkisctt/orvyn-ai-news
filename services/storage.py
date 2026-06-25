import json
import logging
import os
from datetime import datetime, timezone
from typing import Set

logger = logging.getLogger(__name__)


class Storage:
    """Persistent storage for tracking posted news links."""

    def __init__(self, file_path: str = "posted_news.json"):
        self.file_path = file_path
        self.posted_links: Set[str] = set()
        self.is_first_run: bool = not os.path.exists(file_path)
        self.load()

    def load(self):
        """Load posted links from the JSON file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.posted_links = set(data.get("links", []))
                    logger.info(
                        f"Loaded {len(self.posted_links)} posted links from storage"
                    )
            else:
                logger.info(
                    "No storage file found — this is a first run. "
                    "Current news will be marked as seen."
                )
        except json.JSONDecodeError:
            logger.warning(
                "Storage file is corrupted. Starting with empty storage."
            )
            self.posted_links = set()
            self.is_first_run = True
        except Exception as e:
            logger.error(f"Error loading storage: {e}")
            self.posted_links = set()

    def save(self):
        """Save posted links to the JSON file."""
        try:
            data = {
                "links": list(self.posted_links),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "count": len(self.posted_links),
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving storage: {e}")

    def is_posted(self, link: str) -> bool:
        """Check if a news link has already been posted."""
        return link in self.posted_links

    def mark_posted(self, link: str):
        """Mark a news link as posted."""
        self.posted_links.add(link)

    def mark_many_posted(self, links):
        """Mark multiple links as posted."""
        for link in links:
            self.posted_links.add(link)
        self.save()

    def mark_posted_and_save(self, link: str):
        """Mark a link as posted and immediately save."""
        self.posted_links.add(link)
        self.save()

    def cleanup_old(self, max_items: int = 2000):
        """Keep storage from growing indefinitely."""
        if len(self.posted_links) > max_items:
            # Convert to sorted list, keep most recent
            links_list = list(self.posted_links)
            self.posted_links = set(links_list[-max_items:])
            self.save()
            logger.info(
                f"Cleaned up storage: kept {len(self.posted_links)} items"
            )

    def get_stats(self) -> dict:
        """Return storage statistics."""
        return {
            "total_posted": len(self.posted_links),
            "file_exists": os.path.exists(self.file_path),
            "is_first_run": self.is_first_run,
        }