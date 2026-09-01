import os
import requests
from src.config import Config
from src.logger import log
from src.cleaner import remove_comments_and_docstrings

class GroqSolver:
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model_name = model_name or Config.GROQ_MODEL
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def generate_solution(self, problem_details: dict) -> str:
        """Generates pure Python 3 solution using Groq models with fallback chain."""
        if not self.api_key:
            log.warning("⚠️ GROQ_API_KEY is not configured. Skipping Groq solver.")
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
            sys_content = "You are a competitive SQL query optimization solver. Output ONLY pure, raw, optimal MySQL 8.0 SQL code without any comments or docstrings."
        else:
            prompt = f"""You are a competitive programming world champion.
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
            sys_content = "You are a competitive programming solver. Output ONLY pure, raw, optimal Python 3 code without any comments or docstrings."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": sys_content
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }

        models_to_try = [
            self.model_name,
            "qwen/qwen3.6-27b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b"
        ]
        models_to_try = list(dict.fromkeys(models_to_try))

        for model in models_to_try:
            payload["model"] = model
            try:
                log.info(f"⚡ Prompting Groq Solver with model '{model}'...")
                res = requests.post(self.api_url, headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["choices"][0]["message"]["content"]
                    clean_code = remove_comments_and_docstrings(raw_text, language=lang_type)
                    log.info(f"✅ Groq solution generated successfully ({model}).")
                    return clean_code
                else:
                    log.warning(f"⚠️ Groq ({model}) status {res.status_code}: {res.text[:120]}. Trying fallback...")
            except Exception as e:
                log.warning(f"⚠️ Groq error ({model}): {e}. Trying fallback...")

        log.error("❌ All Groq models failed or rate-limited.")
        return ""

    def refine_solution(self, problem_details: dict, previous_code: str, error_context: str) -> str:
        """Refines code using Groq models based on failed testcase feedback."""
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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a competitive programming solver. Output ONLY pure, raw, optimal {lang_type} code without comments or docstrings."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }

        models_to_try = [
            self.model_name,
            "qwen/qwen3.6-27b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b"
        ]
        models_to_try = list(dict.fromkeys(models_to_try))

        for model in models_to_try:
            payload["model"] = model
            try:
                log.info(f"🔄 Groq refining solution with model '{model}'...")
                res = requests.post(self.api_url, headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["choices"][0]["message"]["content"]
                    clean_code = remove_comments_and_docstrings(raw_text, language=lang_type)
                    log.info(f"✅ Groq refined solution generated successfully ({model}).")
                    return clean_code
            except Exception as e:
                log.warning(f"⚠️ Groq refinement error ({model}): {e}")

        return previous_code
