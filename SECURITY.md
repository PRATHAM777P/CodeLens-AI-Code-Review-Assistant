# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x.x   | ✅ Active  |
| 1.x.x   | ❌ EOL     |

---

## API Key & Secret Management

**Never hardcode API keys in source files.** This project reads the OpenAI API key exclusively from the `OPENAI_API_KEY` environment variable.

```bash
# ✅ Correct — set it in your shell before running
export OPENAI_API_KEY="sk-..."

# ❌ Wrong — never do this in code or config files
openai.api_key = "sk-..."
```

If you accidentally committed a key, **revoke it immediately** at [platform.openai.com](https://platform.openai.com/api-keys) and generate a new one.

---

## What This Project Does to Stay Secure

- **No key in code** — API key is only read from environment variables via `os.getenv()`.
- **Rate limiting** — Flask backend enforces per-IP rate limits (10 req/min on `/analyze`) to prevent abuse.
- **Input validation** — Code length is capped at 50,000 characters; language values are validated against an allow-list.
- **CORS restriction** — Only `localhost` origins are allowed by default. Set `ALLOWED_ORIGINS` to restrict further.
- **HTML escaping** — All output inserted into the DOM uses `textContent` or an `escHtml()` helper to prevent XSS.
- **No eval / innerHTML on untrusted data** — Frontend never uses `eval()` or raw `innerHTML` on server-returned content.
- **Temp files cleaned up** — All temporary files used for linting are deleted in `finally` blocks.
- **Temp paths stripped from output** — Temp file paths are replaced with `<code>` before returning to the client.
- **Debug mode off by default** — `FLASK_DEBUG` defaults to `false`. Never enable debug mode in production.

---

## Reporting a Vulnerability

If you discover a security issue, **please do not open a public GitHub issue.**

Instead:

1. Email the maintainer privately (see GitHub profile for contact).
2. Include: description of the issue, reproduction steps, potential impact, and any suggested fixes.
3. You will receive an acknowledgement within **48 hours** and a resolution timeline within **7 days**.

We appreciate responsible disclosure and will credit reporters (with permission) in the changelog.

---

## Known Limitations

- This tool is designed for **local development use only**. Do not expose the Flask backend to the public internet without adding authentication.
- The `/analyze` endpoint runs linting tools (`pylint`, `bandit`) in subprocesses. Code is written to temp files with restricted suffixes. Malicious code cannot execute during static analysis, but avoid running this service with elevated permissions.
- Java Checkstyle support depends on an external binary. Ensure you download Checkstyle from the [official source](https://checkstyle.sourceforge.io/) only.
