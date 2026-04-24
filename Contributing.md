# Contributing to Code Review Assistant

Thank you for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/code-review-assistant.git
cd code-review-assistant
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp .env.example .env             # fill in your OPENAI_API_KEY
```

## Running Locally

```bash
cd backend
python app.py
# Open frontend/index.html in a browser or use VS Code Live Server
```

## Pull Request Guidelines

- One feature / fix per PR.
- Add or update tests if applicable.
- Keep `analysis.py` functions focused and well-documented.
- Never commit `.env` or any file containing secrets.
- Run `pylint backend/` and `bandit -r backend/` before submitting.

## Reporting Bugs

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behaviour
- Python version, OS, relevant dependency versions

## Feature Requests

Open an issue with the `enhancement` label. Describe the use case, not just the solution.

## Code Style

- Python: PEP 8, max line length 100.
- JavaScript: 2-space indent, `const`/`let` only, no `var`.
- Comments in English.
