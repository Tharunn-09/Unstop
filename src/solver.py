import re
import warnings

# Suppress deprecation warning if legacy package is imported
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
    HAS_LEGACY_GENAI = False
except ImportError:
    HAS_NEW_GENAI = False
    try:
        import google.generativeai as legacy_genai
        HAS_LEGACY_GENAI = True
    except ImportError:
        HAS_LEGACY_GENAI = False

from src.config import Config
from src.logger import log
from src.cleaner import remove_comments_and_docstrings

class CodingSolver:
    def __init__(self):
        self.client = None
        self.legacy_model = None

        if not (HAS_NEW_GENAI or HAS_LEGACY_GENAI):
            log.warning("⚠️ No Gemini SDK found. Please run: pip install -r requirements.txt")
            return

        if Config.GEMINI_API_KEY:
            if HAS_NEW_GENAI:
                self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
            elif HAS_LEGACY_GENAI:
                legacy_genai.configure(api_key=Config.GEMINI_API_KEY)
                self.legacy_model = legacy_genai.GenerativeModel(Config.GEMINI_MODEL)

    def _call_model(self, prompt: str) -> str:
        """Calls Gemini API with automatic fallback on 503/high-demand errors."""
        models_to_try = [
            Config.GEMINI_MODEL,
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash",
            "gemini-3.1-pro-preview"
        ]
        models_to_try = list(dict.fromkeys(models_to_try))

        last_error = None
        for model_name in models_to_try:
            try:
                log.info(f"🧠 Prompting Gemini Solver with model '{model_name}'...")
                if self.client:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    return response.text
                elif self.legacy_model:
                    response = legacy_genai.GenerativeModel(model_name).generate_content(prompt)
                    return response.text
            except Exception as e:
                log.warning(f"⚠️ Model '{model_name}' encountered: {e}. Trying fallback model...")
                last_error = e

        raise last_error or ValueError("Gemini API key is not configured or SDK is missing.")

    def generate_solution(self, problem_details: dict) -> str:
        """Generates a pure Python 3 solution for the given Unstop problem."""
        if not (self.client or self.legacy_model):
            log.warning("⚠️ GEMINI_API_KEY is not configured.")
            return ""

        title = problem_details.get("title", "Problem")
        description = problem_details.get("description", "")
        examples = problem_details.get("examples", [])
        starter_code = problem_details.get("starter_code", "")
        lang_type = problem_details.get("language_type", "python3")

        examples_text = ""
        if isinstance(examples, list):
            for i, ex in enumerate(examples, 1):
                if isinstance(ex, dict):
                    inp = ex.get("input", "")
                    out = ex.get("output", "")
                    examples_text += f"\nExample {i}:\nInput:\n{inp}\nOutput:\n{out}\n"
                else:
                    examples_text += f"\nExample {i}:\n{ex}\n"

        if lang_type == "mysql":
            prompt = f"""You are a world-class SQL / MySQL database optimization master.
Write a 100% optimal and correct MySQL 8.0 query for the following database problem.

Problem Title: {title}

Problem Description:
{description}

Sample Examples / Schema:
{examples_text}

CRITICAL RULES:
1. Return 100% PURE, EXECUTABLE SQL query ONLY.
2. DO NOT write any comments (NO `--`, NO `/* */`, NO `#`).
3. DO NOT write any explanations or conversational text.
4. Exact Column Names: Ensure all column aliases in the SELECT clause match the requested output format EXACTLY.
5. Exact Formatting: If rounding or decimal format is specified (e.g. DECIMAL(7,2) or 2 decimal places), ensure proper precision (e.g., CAST(ROUND(...) AS DECIMAL(10,2)) or ROUND(..., 2)).
6. The output must be a valid SQL statement ending with a semicolon `;`.
7. Enclose your final pure SQL inside a single ```sql code block.
"""
        else:
            prompt = f"""You are a world-class competitive programming master.
Solve the following coding problem in Python 3 with optimal $O(N)$ or $O(N \\log N)$ time complexity.

Problem Title: {title}

Problem Description:
{description}

Sample Examples:
{examples_text}

Starter Code Template:
{starter_code if starter_code else "No template provided. Use standard I/O (sys.stdin.read().split()) and print result."}

CRITICAL RULES:
1. Return 100% PURE, EXECUTABLE Python 3 code ONLY.
2. DO NOT write any comments (NO `#` comments whatsoever).
3. DO NOT write any docstrings (NO triple-quotes).
4. DO NOT write any explanations or conversational text.
5. If a starter code template with `user_logic(...)` and `main()` was provided, keep the exact same function signatures and implement logic inside `user_logic(...)`.
6. Enclose your final pure code inside a single ```python code block.
"""

        try:
            raw_text = self._call_model(prompt)
            clean_code = remove_comments_and_docstrings(raw_text, language=lang_type)
            log.info(f"✅ Gemini solution generated successfully ({lang_type}).")
            return clean_code
        except Exception as e:
            log.error(f"❌ Failed to generate solution via Gemini: {e}")
            return ""

    def refine_solution(self, problem_details: dict, previous_code: str, error_context: str) -> str:
        """Refines code based on failed testcase feedback or runtime error."""
        title = problem_details.get("title", "Problem")
        description = problem_details.get("description", "")
        examples = problem_details.get("examples", [])
        starter_code = problem_details.get("starter_code", "")
        lang_type = problem_details.get("language_type", "python3")

        examples_text = ""
        if isinstance(examples, list):
            for i, ex in enumerate(examples, 1):
                if isinstance(ex, dict):
                    inp = ex.get("input", "")
                    out = ex.get("output", "")
                    examples_text += f"\nExample {i}:\nInput:\n{inp}\nOutput:\n{out}\n"
                else:
                    examples_text += f"\nExample {i}:\n{ex}\n"

        prompt = f"""You are a competitive programming world champion.
Your previous solution for '{title}' failed with the following error:

FAILURE DETAILS / FAILED TESTCASE:
{error_context}

PREVIOUS CODE THAT FAILED:
```
{previous_code}
```

PROBLEM STATEMENT:
{description}

SAMPLE EXAMPLES:
{examples_text}

STARTER TEMPLATE:
{starter_code}

TASK:
1. Fix all bugs, off-by-one errors, formatting mismatches, recursion depth issues, or edge cases.
2. Return 100% PURE, EXECUTABLE {lang_type.upper()} code ONLY.
3. DO NOT write any comments (NO `#` comments).
4. DO NOT write any docstrings or conversational text.
5. Enclose your final pure code inside a single ```{lang_type if lang_type != 'python3' else 'python'} code block.
"""
        try:
            log.info(f"🔄 Gemini refining solution based on testcase failure feedback...")
            raw_text = self._call_model(prompt)
            clean_code = remove_comments_and_docstrings(raw_text, language=lang_type)
            log.info(f"✅ Gemini refined solution generated.")
            return clean_code
        except Exception as e:
            log.error(f"❌ Failed to refine solution via Gemini: {e}")
            return previous_code

