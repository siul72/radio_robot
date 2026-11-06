from __future__ import annotations
from enum import Enum


class CrawlType(str, Enum):
    RSS = "rss"
    WEBSITE = "website"
    SITEMAP = "sitemap"
    API = "api"

class NewsType(str, Enum):
    EVENTS_JSON = "events_json"
    RSS = "rss"
    WEBSITE = "website"
    API = "api"
 
    @classmethod
    def from_str(cls, value: str) -> NewsType:
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            raise ValueError(
                f"Invalid news type '{value}'. "
                f"Valid values are: {', '.join(t.value for t in cls)}"
            )