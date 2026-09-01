import ast
import re

def remove_sql_comments(source_code: str) -> str:
    """
    Strips all comments (-- ..., /* ... */, # ...) and markdown fences from SQL code.
    Returns 100% pure executable SQL query.
    """
    text = source_code.strip()

    # 1. Strip markdown fences if present
    fence_match = re.search(r"```(?:sql|mysql)?\s*\n([\s\S]*?)\n```", text, re.MULTILINE | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        blocks = re.findall(r"```(?:sql|mysql)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if blocks:
            text = blocks[0].strip()

    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text).strip()

    # 2. Strip thinking blocks
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL).strip()

    # 3. Strip multiline C/SQL comments /* ... */
    text = re.sub(r'/\*[\s\S]*?\*/', '', text)

    # 4. Strip single-line comments (-- ... and # ...)
    cleaned_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--") or stripped.startswith("#"):
            continue
        # Remove trailing inline comment -- or #
        line_no_comment = re.sub(r'--.*$', '', line)
        line_no_comment = re.sub(r'#.*$', '', line_no_comment)
        if line_no_comment.strip():
            cleaned_lines.append(line_no_comment.rstrip())

    clean_sql = "\n".join(cleaned_lines).strip()
    if clean_sql and not clean_sql.endswith(";"):
        clean_sql += ";"
    return clean_sql

def remove_comments_and_docstrings(source_code: str, language: str = "python3") -> str:
    """
    Strips all comments, docstrings, and markdown fences based on language.
    Returns 100% pure executable code.
    """
    if str(language).lower() in ["mysql", "sql"]:
        return remove_sql_comments(source_code)

    text = source_code.strip()

    # 1. Strip markdown fences if present
    fence_match = re.search(r"```(?:python|py)?\s*\n([\s\S]*?)\n```", text, re.MULTILINE)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        # Fallback regex for code blocks
        blocks = re.findall(r"```(?:python|py)?\s*([\s\S]*?)```", text)
        if blocks:
            text = blocks[0].strip()

    # Remove any stray backticks
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text).strip()

    # 2. Strip thinking blocks (e.g. <think>...</think> from DeepSeek/Qwen)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL).strip()

    # 3. Strip Python comments (# ...)
    cleaned_lines = []
    in_multiline_string = False
    quote_char = None

    for line in text.split("\n"):
        stripped_line = line.strip()
        # Skip pure comment lines
        if stripped_line.startswith("#"):
            continue
        
        # Remove inline comments (safely checking if # is inside string)
        new_chars = []
        in_single_quote = False
        in_double_quote = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "'" and (i == 0 or line[i-1] != "\\") and not in_double_quote:
                in_single_quote = not in_single_quote
            elif ch == '"' and (i == 0 or line[i-1] != "\\") and not in_single_quote:
                in_double_quote = not in_double_quote
            elif ch == '#' and not in_single_quote and not in_double_quote:
                # Comment starts here, truncate remainder
                break
            new_chars.append(ch)
            i += 1

        cleaned_line = "".join(new_chars).rstrip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    clean_code = "\n".join(cleaned_lines)

    # 4. Remove Docstrings using AST transformations if valid Python
    try:
        parsed = ast.parse(clean_code)
        for node in ast.walk(parsed):
            # If docstring in module, class, or function
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)):
                    # Replace docstring Expr with Pass if body becomes empty, else delete
                    if len(node.body) > 1:
                        node.body.pop(0)
                    else:
                        node.body[0] = ast.Pass()
        clean_code = ast.unparse(parsed)
    except Exception:
        # Fallback regex for docstrings if ast parsing had minor syntax variations
        clean_code = re.sub(r'"""[\s\S]*?"""', '', clean_code)
        clean_code = re.sub(r"'''[\s\S]*?'''", '', clean_code)
        # Re-filter empty lines
        clean_code = "\n".join([l for l in clean_code.split("\n") if l.strip()])

    return clean_code.strip()
