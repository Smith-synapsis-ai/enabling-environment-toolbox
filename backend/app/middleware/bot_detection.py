"""Bot detection utilities.

Provides a function to check whether a User-Agent string belongs to a
known web crawler or bot.  The pattern list covers the most common
search-engine crawlers, social-media preview bots, and generic
scraping frameworks.
"""

import re
from typing import Optional

# ~50 known bot / crawler user-agent substrings (case-insensitive)
BOT_PATTERNS: list[str] = [
    # Search engine crawlers
    "googlebot",
    "bingbot",
    "slurp",           # Yahoo
    "duckduckbot",
    "baiduspider",
    "yandexbot",
    "sogou",
    "exabot",
    "ia_archiver",     # Alexa
    "applebot",
    "petalbot",        # Huawei
    "qwantify",
    "seznambot",
    "mojeekbot",
    # Social media / preview bots
    "facebookexternalhit",
    "facebot",
    "twitterbot",
    "linkedinbot",
    "whatsapp",
    "slackbot",
    "telegrambot",
    "discordbot",
    "pinterestbot",
    # Monitoring / uptime
    "uptimerobot",
    "pingdom",
    "statuscake",
    "site24x7",
    "newrelicpinger",
    "datadogagent",
    # SEO / analytics tools
    "semrushbot",
    "ahrefsbot",
    "mj12bot",          # Majestic
    "dotbot",
    "rogerbot",         # Moz
    "screaming frog",
    # Generic patterns
    "crawler",
    "spider",
    "bot/",
    "bot;",
    "scraper",
    "headlesschrome",
    "phantomjs",
    "python-requests",
    "python-urllib",
    "wget",
    "curl/",
    "http-client",
    "go-http-client",
    "java/",
    "libwww",
    "apache-httpclient",
]

# Compile a single case-insensitive regex for performance
_BOT_REGEX = re.compile(
    "|".join(re.escape(p) for p in BOT_PATTERNS),
    re.IGNORECASE,
)


def is_bot_user_agent(ua: Optional[str]) -> bool:
    """Return True if the user-agent string matches a known bot pattern."""
    if not ua:
        return False
    return bool(_BOT_REGEX.search(ua))
