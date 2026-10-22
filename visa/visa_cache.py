"""
Visa Data Caching Subsystem.
Caches retrieved live visa information, country profiles, and official portal checks
to ensure high throughput, reduce external network overhead, and provide offline resilience.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from config.api_config import api_config
from src.utils.logging_config import logger


class VisaCacheManager:
    def __init__(self, cache_file: Optional[Path] = None, ttl_hours: Optional[int] = None):
        self.cache_file = cache_file or api_config.CACHE_FILE
        self.ttl_seconds = (ttl_hours or api_config.CACHE_TTL_HOURS) * 3600
        self._memory_cache: Dict[str, Any] = {}
        self._last_loaded: float = 0.0
        self._ensure_cache_dir()
        self._load_from_disk()

    def _ensure_cache_dir(self) -> None:
        """Ensures that the cache directory exists."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create cache directory {self.cache_file.parent}: {e}")

    def _load_from_disk(self) -> None:
        """Loads cached JSON data from disk if present."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._memory_cache = data
                        self._last_loaded = time.time()
                        logger.info(f"Loaded {len(self._memory_cache)} cached items from {self.cache_file}")
            except Exception as e:
                logger.error(f"Error reading visa cache file {self.cache_file}: {e}")
                self._memory_cache = {}

    def _save_to_disk(self) -> None:
        """Flushes memory cache to disk atomically."""
        try:
            self._ensure_cache_dir()
            tmp_file = self.cache_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._memory_cache, f, indent=2, ensure_ascii=False)
            tmp_file.replace(self.cache_file)
        except Exception as e:
            logger.error(f"Failed to persist visa cache to {self.cache_file}: {e}")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a cached value if exists and not expired.
        Returns None if cache miss or expired.
        """
        entry = self._memory_cache.get(key)
        if not entry or not isinstance(entry, dict):
            return None

        cached_time = entry.get("timestamp", 0)
        ttl = entry.get("ttl_seconds", self.ttl_seconds)

        if (time.time() - cached_time) > ttl:
            # Expired
            return None

        return entry.get("data")

    def set(self, key: str, data: Any, source: str = "Official Immigration Portal", ttl_seconds: Optional[int] = None) -> None:
        """Stores data in memory and persists to disk."""
        now = time.time()
        self._memory_cache[key] = {
            "data": data,
            "source": source,
            "timestamp": now,
            "iso_timestamp": datetime.now().strftime("%d %B %Y, %H:%M"),
            "ttl_seconds": ttl_seconds or self.ttl_seconds
        }
        self._save_to_disk()

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Returns metadata regarding cached entry (timestamp, source, freshness)."""
        entry = self._memory_cache.get(key)
        if not entry:
            return None
        cached_time = entry.get("timestamp", 0)
        is_fresh = (time.time() - cached_time) <= entry.get("ttl_seconds", self.ttl_seconds)
        return {
            "source": entry.get("source"),
            "timestamp": entry.get("timestamp"),
            "iso_timestamp": entry.get("iso_timestamp"),
            "is_fresh": is_fresh
        }

    def clear(self) -> None:
        """Clears memory and disk cache."""
        self._memory_cache = {}
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete cache file: {e}")
        logger.info("Visa cache cleared successfully.")

    def get_status(self) -> Dict[str, Any]:
        """Returns general diagnostic status of the cache."""
        item_count = len(self._memory_cache)
        latest_ts = 0
        latest_iso = "N/A"
        for v in self._memory_cache.values():
            if isinstance(v, dict) and v.get("timestamp", 0) > latest_ts:
                latest_ts = v.get("timestamp", 0)
                latest_iso = v.get("iso_timestamp", "N/A")

        return {
            "cached_entries": item_count,
            "cache_file": str(self.cache_file),
            "cache_file_exists": self.cache_file.exists(),
            "latest_update": latest_iso,
            "ttl_hours": int(self.ttl_seconds / 3600)
        }


visa_cache = VisaCacheManager()
