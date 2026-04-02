import tempfile
import subprocess
import os
import openai
import logging

logger = logging.getLogger(__name__)

def get_openai_api_key():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError('OpenAI API key not set. Please set the OPENAI_API_KEY environment variable.')
    return api_key

def run_pylint(code):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.py', mode='w', encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run([
            'pylint', tmp_path, '--disable=all', '--enable=E,W,C,R', '--output-format=text', '--score=n'
        ], capture_output=True, text=True, timeout=10)
        output = result.stdout
        messages = [line for line in output.splitlines() if line.strip() and not line.startswith(('*********', 'Your code', '------------------------------------------------------------------'))]
        if not messages:
            messages = ['No issues found.']
        return messages
    finally:
        os.unlink(tmp_path)

def run_bandit(code):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.py', mode='w', encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run([
            'bandit', '-q', '-r', tmp_path, '--format', 'short'
        ], capture_output=True, text=True, timeout=10)
        output = result.stdout
        issues = [line for line in output.splitlines() if line.strip() and not line.startswith(('Run started', 'Test results', 'Code scanned', 'Total issues'))]
        if not issues:
            issues = ['No security risks detected.']
        return issues
    finally:
        os.unlink(tmp_path)

def run_checkstyle(code):
    # Save code to a temporary .java file and run Checkstyle if available
    with tempfile.NamedTemporaryFile(delete=False, suffix='.java', mode='w', encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        # Assumes checkstyle is installed and checkstyle.xml config is available
        result = subprocess.run([
            'checkstyle', '-c', '/google_checks.xml', tmp_path
        ], capture_output=True, text=True, timeout=10)
        output = result.stdout
        messages = [line for line in output.splitlines() if line.strip()]
        if not messages:
            messages = ['No issues found.']
        return messages
    except Exception as e:
        logger.exception("Error while running Checkstyle")
        return ['Checkstyle error: internal error while running Checkstyle.']
    finally:
        os.unlink(tmp_path)

def run_openai_suggestions(code, language):
    openai.api_key = get_openai_api_key()
    prompt = (
        f"You are a code review assistant. Given the following {language} code, suggest improvements for readability, maintainability, and best practices. "
        "Only return actionable suggestions as a list.\n\nCode:\n" + code
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.2
        )
        suggestions = response.choices[0].message['content'].strip().split('\n')
        # Clean up suggestions (remove empty lines, bullets, etc.)
        suggestions = [s.lstrip('-• ').strip() for s in suggestions if s.strip()]
        if not suggestions:
            suggestions = ['No suggestions at this time.']
        return suggestions
    except Exception as e:
        logger.exception("Error while getting OpenAI suggestions")
        return ['Error from OpenAI: internal error while generating suggestions.']

def run_openai_custom_prompt(code, language, prompt):
    openai.api_key = get_openai_api_key()
    full_prompt = f"You are a code review assistant. The user has a question about their {language} code.\n\nCode:\n{code}\n\nQuestion: {prompt}\n\nAnswer:"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=256,
            temperature=0.2
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logger.exception("Error while processing OpenAI custom prompt")
        return 'Error from OpenAI: internal error while processing custom prompt.'

def analyze_code(code, language='python', prompt=None):
    if language == 'python':
        quality = run_pylint(code)
        security = run_bandit(code)
        suggestions = run_openai_suggestions(code, language)
    elif language == 'java':
        quality = run_checkstyle(code)
        security = ['Java security scanning not implemented.']
        suggestions = run_openai_suggestions(code, language)
    else:
        quality = [f'No linter configured for {language}.']
        security = [f'No security scanner configured for {language}.']
        suggestions = run_openai_suggestions(code, language)
    custom_ai_response = None
    if prompt:
        custom_ai_response = run_openai_custom_prompt(code, language, prompt)
    return {
        'quality': quality,
        'security': security,
        'suggestions': suggestions,
        'custom_ai_response': custom_ai_response
    } 