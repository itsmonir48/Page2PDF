"""
Page2PDF — Code Processor
Handles syntax highlighting and code block formatting for PDFs.
"""

import re
import logging
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def highlight_code(code: str, language: Optional[str] = None) -> str:
    """
    Apply syntax highlighting to a code string.
    Returns HTML with inline styles for syntax highlighting.
    """
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
        from pygments.formatters import HtmlFormatter
        from pygments.util import ClassNotFound

        # Try to get lexer by language name
        lexer = None
        if language:
            try:
                lexer = get_lexer_by_name(language.lower(), stripall=True)
            except ClassNotFound:
                pass

        # Try to guess the language
        if not lexer:
            try:
                lexer = guess_lexer(code)
            except Exception:
                lexer = TextLexer()

        # Use inline styles (WeasyPrint doesn't load external CSS for highlighted code)
        formatter = HtmlFormatter(
            style="monokai",
            noclasses=True,
            nowrap=False,
            linenos=False,
            prestyles=(
                "background-color: #1e1e2e; "
                "color: #cdd6f4; "
                "padding: 16px 20px; "
                "border-radius: 8px; "
                "font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace; "
                "font-size: 13px; "
                "line-height: 1.6; "
                "overflow-x: auto; "
                "white-space: pre; "
                "margin: 12px 0; "
                "border-left: 4px solid #89b4fa; "
            ),
        )

        highlighted = highlight(code, lexer, formatter)
        return highlighted

    except ImportError:
        logger.warning("Pygments not available, using plain code formatting")
        return _format_plain_code(code)
    except Exception as e:
        logger.error(f"Syntax highlighting error: {e}")
        return _format_plain_code(code)


def _format_plain_code(code: str) -> str:
    """Format code without syntax highlighting."""
    import html
    escaped = html.escape(code)
    return (
        f'<pre style="background-color: #1e1e2e; color: #cdd6f4; padding: 16px 20px; '
        f'border-radius: 8px; font-family: monospace; font-size: 13px; line-height: 1.6; '
        f'overflow-x: auto; white-space: pre; margin: 12px 0; border-left: 4px solid #89b4fa;">'
        f'<code>{escaped}</code></pre>'
    )


def process_code_blocks(html_content: str) -> str:
    """
    Find all code blocks in HTML content and apply syntax highlighting.
    """
    if not html_content:
        return html_content

    soup = BeautifulSoup(html_content, "html.parser")

    for pre in soup.find_all("pre"):
        code_tag = pre.find("code")
        if code_tag:
            code_text = code_tag.get_text()
            # Detect language from class
            language = _detect_language(code_tag.get("class", []))
            highlighted = highlight_code(code_text, language)

            # Replace the pre block with highlighted version
            new_soup = BeautifulSoup(highlighted, "html.parser")
            pre.replace_with(new_soup)
        else:
            code_text = pre.get_text()
            if code_text.strip():
                highlighted = highlight_code(code_text)
                new_soup = BeautifulSoup(highlighted, "html.parser")
                pre.replace_with(new_soup)

    # Handle inline code elements (not inside pre)
    for code in soup.find_all("code"):
        if code.parent and code.parent.name != "pre":
            code_text = code.get_text()
            code["style"] = (
                "background-color: #313244; color: #f38ba8; padding: 2px 6px; "
                "border-radius: 4px; font-family: 'JetBrains Mono', monospace; "
                "font-size: 0.9em;"
            )

    return str(soup)


def _detect_language(classes: list) -> Optional[str]:
    """Detect programming language from CSS classes."""
    if not classes:
        return None

    for cls in classes:
        cls_lower = cls.lower()
        # Handle common patterns like "language-python", "lang-py", "hljs-python"
        for prefix in ["language-", "lang-", "hljs-", "highlight-"]:
            if cls_lower.startswith(prefix):
                lang = cls_lower[len(prefix):]
                return _normalize_language(lang)
        # Direct language name
        normalized = _normalize_language(cls_lower)
        if normalized:
            return normalized

    return None


def _normalize_language(lang: str) -> Optional[str]:
    """Normalize language identifier."""
    lang_map = {
        "py": "python",
        "python3": "python",
        "js": "javascript",
        "ts": "typescript",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "yml": "yaml",
        "dockerfile": "docker",
        "makefile": "make",
        "md": "markdown",
        "rb": "ruby",
        "rs": "rust",
        "kt": "kotlin",
        "cs": "csharp",
        "c#": "csharp",
        "c++": "cpp",
        "cc": "cpp",
        "h": "c",
        "hpp": "cpp",
        "jsx": "javascript",
        "tsx": "typescript",
        "m": "objectivec",
        "mm": "objectivec",
        "r": "r",
        "pl": "perl",
        "lua": "lua",
        "ex": "elixir",
        "exs": "elixir",
        "hs": "haskell",
        "erl": "erlang",
        "clj": "clojure",
        "sc": "scala",
        "scala": "scala",
        "swift": "swift",
        "dart": "dart",
    }

    lang = lang.strip().lower()
    if lang in lang_map:
        return lang_map[lang]
    if lang in lang_map.values():
        return lang
    # Common language names
    known = {
        "python", "javascript", "typescript", "java", "c", "cpp", "csharp",
        "html", "css", "sql", "bash", "json", "xml", "yaml", "markdown",
        "go", "rust", "ruby", "php", "kotlin", "swift", "dart", "r",
        "perl", "lua", "haskell", "erlang", "clojure", "scala",
        "objectivec", "matlab", "fortran", "assembly",
    }
    if lang in known:
        return lang
    return None
