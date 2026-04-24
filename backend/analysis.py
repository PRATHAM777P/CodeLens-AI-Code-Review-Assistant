"""
Code Review Assistant - Analysis Engine
Supports: Python, Java, JavaScript, TypeScript, C, C++, Go, Rust
"""

import tempfile
import subprocess
import os
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# API key helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_openai_api_key() -> str:
    """Read OpenAI API key from environment — never from code."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Export it as an environment variable before starting the server."
        )
    return api_key


# ──────────────────────────────────────────────────────────────────────────────
# Static analysis helpers
# ──────────────────────────────────────────────────────────────────────────────

def _write_temp(code: str, suffix: str) -> str:
    """Write code to a temp file and return the path. Caller must delete it."""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        return tmp.name


def _run(cmd: list, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _clean_lines(output: str, skip_prefixes: tuple = ()) -> list[str]:
    lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in skip_prefixes):
            continue
        lines.append(stripped)
    return lines


# ──────────────────────────────────────────────────────────────────────────────
# Linters / security scanners
# ──────────────────────────────────────────────────────────────────────────────

def run_pylint(code: str) -> list[str]:
    tmp = _write_temp(code, ".py")
    try:
        result = _run([
            "pylint", tmp,
            "--disable=all", "--enable=E,W,C,R",
            "--output-format=text", "--score=n",
        ])
        skip = ("*********", "Your code", "-----")
        msgs = _clean_lines(result.stdout, skip)
        # Strip temp file path from messages for security
        msgs = [m.replace(tmp, "<code>") for m in msgs]
        return msgs or ["✅ No quality issues found."]
    except FileNotFoundError:
        return ["⚠️ pylint is not installed. Run: pip install pylint"]
    except subprocess.TimeoutExpired:
        return ["⚠️ pylint timed out."]
    finally:
        os.unlink(tmp)


def run_bandit(code: str) -> list[str]:
    tmp = _write_temp(code, ".py")
    try:
        result = _run([
            "bandit", "-q", "-r", tmp, "--format", "short"
        ])
        skip = ("Run started", "Test results", "Code scanned", "Total issues")
        issues = _clean_lines(result.stdout, skip)
        issues = [i.replace(tmp, "<code>") for i in issues]
        return issues or ["✅ No security risks detected."]
    except FileNotFoundError:
        return ["⚠️ bandit is not installed. Run: pip install bandit"]
    except subprocess.TimeoutExpired:
        return ["⚠️ bandit timed out."]
    finally:
        os.unlink(tmp)


def run_eslint(code: str) -> list[str]:
    tmp = _write_temp(code, ".js")
    try:
        result = _run(["npx", "--yes", "eslint", "--no-eslintrc", "-c",
                        '{"env":{"es2021":true},"rules":{"no-unused-vars":"warn","no-undef":"warn"}}',
                        tmp])
        msgs = _clean_lines(result.stdout)
        msgs = [m.replace(tmp, "<code>") for m in msgs]
        return msgs or ["✅ No quality issues found."]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ["⚠️ eslint not available. Install Node.js and eslint."]
    finally:
        os.unlink(tmp)


def run_checkstyle(code: str) -> list[str]:
    tmp = _write_temp(code, ".java")
    try:
        result = _run(["checkstyle", "-c", "/google_checks.xml", tmp])
        msgs = _clean_lines(result.stdout)
        msgs = [m.replace(tmp, "<code>") for m in msgs]
        return msgs or ["✅ No quality issues found."]
    except FileNotFoundError:
        return ["ℹ️ Checkstyle not installed — Java quality checks skipped. See README."]
    except subprocess.TimeoutExpired:
        return ["⚠️ Checkstyle timed out."]
    finally:
        os.unlink(tmp)


def run_cppcheck(code: str, suffix: str = ".cpp") -> list[str]:
    tmp = _write_temp(code, suffix)
    try:
        result = _run(["cppcheck", "--enable=all", "--error-exitcode=0", tmp])
        msgs = _clean_lines(result.stderr)
        msgs = [m.replace(tmp, "<code>") for m in msgs if "error" in m or "warning" in m]
        return msgs or ["✅ No issues found."]
    except FileNotFoundError:
        return ["ℹ️ cppcheck not installed — C/C++ quality checks skipped."]
    finally:
        os.unlink(tmp)


def run_govet(code: str) -> list[str]:
    tmpdir = tempfile.mkdtemp()
    tmp = os.path.join(tmpdir, "main.go")
    with open(tmp, "w") as f:
        f.write(code)
    try:
        result = _run(["go", "vet", tmp])
        msgs = _clean_lines(result.stderr)
        msgs = [m.replace(tmp, "<code>") for m in msgs]
        return msgs or ["✅ No issues found."]
    except FileNotFoundError:
        return ["ℹ️ Go is not installed — Go checks skipped."]
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────────
# AI helpers
# ──────────────────────────────────────────────────────────────────────────────

def _call_openai(messages: list[dict], max_tokens: int = 512) -> str:
    import openai  # local import — avoids import error when openai not installed
    openai.api_key = _get_openai_api_key()
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return response.choices[0].message["content"].strip()
    except openai.error.AuthenticationError:
        return "❌ OpenAI authentication failed. Check your OPENAI_API_KEY."
    except openai.error.RateLimitError:
        return "❌ OpenAI rate limit exceeded. Try again later."
    except Exception:
        logger.exception("OpenAI call failed")
        return "❌ OpenAI request failed. Check server logs."


def run_ai_suggestions(code: str, language: str) -> list[str]:
    system = (
        "You are an expert code reviewer. Given code, return ONLY a numbered list "
        "of actionable, specific improvement suggestions (readability, performance, "
        "best practices, error handling). No preamble. Max 8 items."
    )
    user = f"Language: {language}\n\nCode:\n```{language}\n{code[:4000]}\n```"
    raw = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], max_tokens=512)
    lines = [re.sub(r"^[\d]+[.)]\s*", "", s).lstrip("-• ").strip()
             for s in raw.splitlines() if s.strip()]
    return lines or ["No suggestions at this time."]


def run_ai_security_review(code: str, language: str) -> list[str]:
    """AI-powered security review for languages without dedicated scanners."""
    system = (
        "You are a security-focused code reviewer. Identify ONLY real security vulnerabilities: "
        "injection, hardcoded secrets, unsafe deserialization, path traversal, insecure crypto, etc. "
        "Return a numbered list. If none found, say 'No security issues detected.' No preamble."
    )
    user = f"Language: {language}\n\nCode:\n```{language}\n{code[:4000]}\n```"
    raw = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], max_tokens=400)
    lines = [re.sub(r"^[\d]+[.)]\s*", "", s).lstrip("-• ").strip()
             for s in raw.splitlines() if s.strip()]
    return lines or ["✅ No security issues detected."]


def run_ai_complexity(code: str, language: str) -> dict:
    """Return complexity metrics via AI analysis."""
    system = (
        "You are a code complexity analyst. Respond ONLY with a JSON object "
        "(no markdown) with these keys: "
        "\"overall\" (Low/Medium/High/Critical), "
        "\"cyclomatic\" (estimated number), "
        "\"maintainability\" (0-100 score), "
        "\"summary\" (one sentence)."
    )
    user = f"Language: {language}\n\nCode:\n```{language}\n{code[:4000]}\n```"
    raw = _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], max_tokens=200)
    import json
    try:
        clean = re.sub(r"```[a-z]*\n?", "", raw).strip().strip("`")
        return json.loads(clean)
    except Exception:
        return {"overall": "Unknown", "cyclomatic": "N/A", "maintainability": "N/A", "summary": raw}


def run_ai_custom_prompt(code: str, language: str, prompt: str) -> str:
    system = (
        f"You are an expert {language} code reviewer. Answer the user's question "
        "about their code clearly and concisely. Be specific and cite line numbers when relevant."
    )
    user = f"Code:\n```{language}\n{code[:4000]}\n```\n\nQuestion: {prompt}"
    return _call_openai([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], max_tokens=600)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def analyze_code(code: str, language: str = "python", prompt: Optional[str] = None) -> dict:
    """
    Run static analysis + AI review for the given code and language.
    Returns a dict with: quality, security, suggestions, complexity, custom_ai_response
    """
    lang = language.lower()

    # Quality (static linters)
    if lang == "python":
        quality = run_pylint(code)
        security = run_bandit(code)
    elif lang == "java":
        quality = run_checkstyle(code)
        security = run_ai_security_review(code, lang)
    elif lang in ("javascript", "typescript"):
        quality = run_eslint(code)
        security = run_ai_security_review(code, lang)
    elif lang in ("c", "cpp", "c++"):
        quality = run_cppcheck(code, ".c" if lang == "c" else ".cpp")
        security = run_ai_security_review(code, lang)
    elif lang == "go":
        quality = run_govet(code)
        security = run_ai_security_review(code, lang)
    else:
        quality = [f"ℹ️ No static linter configured for {language}."]
        security = run_ai_security_review(code, lang)

    # AI-powered analysis
    try:
        suggestions = run_ai_suggestions(code, lang)
    except Exception:
        logger.exception("AI suggestions failed")
        suggestions = ["⚠️ AI suggestions unavailable."]

    try:
        complexity = run_ai_complexity(code, lang)
    except Exception:
        logger.exception("Complexity analysis failed")
        complexity = {"overall": "Unknown", "summary": "Analysis unavailable."}

    custom_ai_response = None
    if prompt:
        try:
            custom_ai_response = run_ai_custom_prompt(code, lang, prompt)
        except Exception:
            logger.exception("Custom prompt failed")
            custom_ai_response = "⚠️ Custom AI response unavailable."

    return {
        "quality": quality,
        "security": security,
        "suggestions": suggestions,
        "complexity": complexity,
        "custom_ai_response": custom_ai_response,
        "language": lang,
        "lines": len(code.splitlines()),
        "chars": len(code),
    }
