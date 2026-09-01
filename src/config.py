import os
import re
from dotenv import load_dotenv
from src.logger import log

# Load local .env if present
load_dotenv()

class Config:
    # Authentication - paste full cookie string from your browser
    UNSTOP_COOKIES: str = (os.getenv("UNSTOP_COOKIES") or os.getenv("UNSTOP_COOKIE") or "").strip()
    UNSTOP_AUTH_TOKEN: str = os.getenv("UNSTOP_AUTH_TOKEN", "").strip()
    UNSTOP_USER_ID: str = os.getenv("UNSTOP_USER_ID", "").strip()

    # AI Solvers
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b").strip()

    # Email Notifications (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "").strip()
    TO_EMAIL: str = os.getenv("TO_EMAIL", "").strip()
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "Unstop Bot <onboarding@resend.dev>").strip()

    # Question ID or Practice URL (set to "potd" for automatic daily POTD discovery)
    TARGET_QUESTION: str = os.getenv("UNSTOP_QUESTION_ID", "potd").strip()

    # Settings
    PREFERRED_LANGUAGE: str = os.getenv("PREFERRED_LANGUAGE", "python3").strip().lower()
    RUN_MODE: str = os.getenv("RUN_MODE", "live").strip().lower() # 'live' or 'dry-run'

    # Unstop Endpoints
    BASE_URL: str = "https://unstop.com"
    POTD_PAGE_URL: str = "https://unstop.com/practice/potd"

    @classmethod
    def get_target_question_id(cls, input_val: str = None) -> str:
        """Extracts numerical question ID from raw input or URL."""
        val = str(input_val or cls.TARGET_QUESTION).strip()
        # If full URL like https://unstop.com/code/practice/250138
        match = re.search(r'/practice/([0-9]+)', val)
        if match:
            return match.group(1)
        # Match standalone digits
        match_digits = re.search(r'([0-9]+)', val)
        if match_digits:
            return match_digits.group(1)
        return "250138"

    # Language mapping for Unstop submission APIs
    LANGUAGE_IDS = {
        "python3": 71,   # Python 3
        "python": 71,
        "py": 71,
        "cpp": 54,       # C++ (GCC)
        "java": 62,      # Java (OpenJDK)
        "javascript": 63 # JavaScript (Node.js)
    }

    @classmethod
    def get_language_id(cls, lang_name: str = None) -> int:
        target = (lang_name or cls.PREFERRED_LANGUAGE).lower()
        return cls.LANGUAGE_IDS.get(target, 71)

    @classmethod
    def validate(cls) -> bool:
        """Validates critical credentials before running."""
        is_valid = True
        if not cls.GEMINI_API_KEY:
            log.error("Missing GEMINI_API_KEY in environment variables. Get a free API key at https://aistudio.google.com/")
            is_valid = False

        if cls.RUN_MODE == "live" and not cls.UNSTOP_COOKIES and not cls.UNSTOP_AUTH_TOKEN:
            log.warning("⚠️ No UNSTOP_COOKIES found in .env or environment secrets.")
            log.warning("Please provide your login cookies string, or set RUN_MODE='dry-run' for testing.")
            is_valid = False

        return is_valid
