"""
AduScope - App Configuration
Central place for constants: supported languages, API settings, theme colors.
"""

import os

# ---------------------------------------------------------------------------
# AI Configuration (OpenRouter — free tier, no credit card, works everywhere,
# no VPN needed since requests are routed through OpenRouter's servers)
# ---------------------------------------------------------------------------
# NEVER hardcode your real key here. Set it as an environment variable before
# running the app:
#   export OPENROUTER_API_KEY="sk-or-v1-..."          (mac/linux)
#   setx OPENROUTER_API_KEY "sk-or-v1-..."             (windows)
# Get a free key at https://openrouter.ai (sign up, no card needed)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
AI_MODEL =  "meta-llama/llama-3.3-70b-instruct:free" # free tier, strong multilingual quality
MAX_TOKENS = 1024

TOTAL_QUESTIONS = 10

# ---------------------------------------------------------------------------
# Supported Languages (code, native display name)
# 20+ languages as required by the spec
# ---------------------------------------------------------------------------
LANGUAGES = [
    ("am", "አማርኛ"),
    ("en", "English"),
    ("ar", "العربية"),
    ("fr", "Français"),
    ("es", "Español"),
    ("sw", "Kiswahili"),
    ("om", "Afaan Oromoo"),
    ("ti", "ትግርኛ"),
    ("so", "Soomaali"),
    ("de", "Deutsch"),
    ("zh", "中文"),
    ("hi", "हिन्दी"),
    ("pt", "Português"),
    ("ru", "Русский"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("tr", "Türkçe"),
    ("fa", "فارسی"),
    ("ur", "اردو"),
    ("it", "Italiano"),
    ("nl", "Nederlands"),
    ("ha", "Hausa"),
]

# ---------------------------------------------------------------------------
# Theme colors
# ---------------------------------------------------------------------------
LIGHT_THEME = {
    "bg": "#F7F5F2",
    "primary": "#5B3DF5",
    "accent": "#FFB648",
    "text": "#1B1B1F",
    "card": "#FFFFFF",
}

DARK_THEME = {
    "bg": "#0F0E17",
    "primary": "#8C7CFC",
    "accent": "#FFB648",
    "text": "#F2F2F7",
    "card": "#1C1B29",
}
