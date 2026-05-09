import os
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Groq Free Tier — serves Llama 3 models (100% open source, 100% free)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def extract_deadline_and_validate(text: str) -> dict:
    """
    Extracts deadline from text. Uses Llama 3 (via Groq free tier) as primary,
    with local Ollama Llama as backup, and smart regex as final fallback.
    """
    # 1. Try Llama 3 via Groq Cloud (Free Tier — open source model)
    if GROQ_API_KEY:
        llama_result = _try_llama_groq(text)
        if llama_result:
            return llama_result

    # 2. Try Local Llama via Ollama — 100% Free & Private (Local Dev)
    llama_local_result = _try_llama_local(text)
    if llama_local_result:
        return llama_local_result

    # 3. Fallback: Smart regex/keyword-based extraction (no AI needed)
    return _smart_parse_deadline(text)


def _try_llama_groq(text: str) -> dict | None:
    """Use Llama 3 70B via Groq Cloud API (free tier, open source model)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""Extract the registration deadline from the following text.
If there is no registration deadline mentioned, reply with "NONE".
If there is a deadline, format it strictly as YYYY-MM-DD.
Only output the date or NONE. No other text.

Text: {text}"""

    try:
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code == 200:
            result = res.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if result != "NONE" and len(result) <= 12:
                try:
                    deadline_date = datetime.strptime(result, "%Y-%m-%d")
                    return _calculate_priority(deadline_date)
                except ValueError:
                    return None
    except Exception:
        return None
    return None


def _try_llama_local(text: str) -> dict | None:
    """Try to use a local Llama model via Ollama."""
    url = "http://localhost:11434/api/generate"
    prompt = f"""Extract the registration deadline from the following text.
If there is no registration deadline mentioned, reply with "NONE".
If there is a deadline, format it strictly as YYYY-MM-DD.
Only output the date or NONE. No other text.

Text: {text}"""

    try:
        # Short timeout to avoid hanging if Ollama is not running
        res = requests.post(url, json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }, timeout=5)

        if res.status_code == 200:
            result = res.json().get("response", "").strip()
            if result != "NONE" and len(result) <= 12:
                try:
                    deadline_date = datetime.strptime(result, "%Y-%m-%d")
                    return _calculate_priority(deadline_date)
                except ValueError:
                    return None
    except Exception:
        return None
    return None


def _smart_parse_deadline(text: str) -> dict:
    """
    Parse deadline from text using regex patterns and keyword heuristics.
    Works without any AI model.
    """
    text_lower = text.lower().strip()
    today = datetime.now()

    # 1) Try to match explicit ISO date: "Deadline is 2026-05-20T..."
    iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if iso_match:
        try:
            deadline = datetime.strptime(iso_match.group(1), "%Y-%m-%d")
            return _calculate_priority(deadline)
        except ValueError:
            pass

    # 2) Try "Month DD" or "Month DD, YYYY" patterns
    month_match = re.search(
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?',
        text_lower
    )
    if month_match:
        month_str = month_match.group(1)
        day = int(month_match.group(2))
        year = int(month_match.group(3)) if month_match.group(3) else today.year
        try:
            deadline = datetime.strptime(f"{month_str} {day} {year}", "%B %d %Y")
            # If the parsed date is in the past and no year was given, try next year
            if deadline < today and not month_match.group(3):
                deadline = deadline.replace(year=today.year + 1)
            return _calculate_priority(deadline)
        except ValueError:
            pass

    # 3) Try "DD/MM/YYYY" or "MM/DD/YYYY"
    slash_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if slash_match:
        try:
            deadline = datetime.strptime(slash_match.group(0), "%m/%d/%Y")
            return _calculate_priority(deadline)
        except ValueError:
            try:
                deadline = datetime.strptime(slash_match.group(0), "%d/%m/%Y")
                return _calculate_priority(deadline)
            except ValueError:
                pass

    # 4) Keyword-based heuristics for relative dates
    if any(kw in text_lower for kw in ['asap', 'rolling', 'open', 'ongoing']):
        # Rolling/ASAP — treat as 14 days from now (valid, medium priority)
        deadline = today + timedelta(days=14)
        return _calculate_priority(deadline)

    if 'today' in text_lower or 'tonight' in text_lower:
        return _calculate_priority(today)

    if 'tomorrow' in text_lower:
        return _calculate_priority(today + timedelta(days=1))

    if 'next week' in text_lower:
        return _calculate_priority(today + timedelta(days=7))

    if 'next month' in text_lower:
        return _calculate_priority(today + timedelta(days=30))

    # 5) Try to find just a number of days mentioned: "in 5 days"
    days_match = re.search(r'in\s+(\d+)\s+days?', text_lower)
    if days_match:
        days = int(days_match.group(1))
        return _calculate_priority(today + timedelta(days=days))

    # 6) "No deadline" or unrecognized — still mark as valid with generous window
    if 'no deadline' in text_lower:
        return {"deadline_str": None, "is_valid": False, "days_left": None, "priority": "EXPIRED"}

    # Default: treat as valid with 10 days out so it shows up
    deadline = today + timedelta(days=10)
    return _calculate_priority(deadline)


def _calculate_priority(deadline_date: datetime) -> dict:
    today = datetime.now()
    days_left = (deadline_date - today).days

    if days_left < 0:
        return {"deadline_str": deadline_date.strftime("%Y-%m-%d"), "is_valid": False, "days_left": days_left, "priority": "EXPIRED"}
    elif days_left <= 3:
        priority = "🔴 HIGH PRIORITY"
    elif days_left <= 10:
        priority = "🟡 MEDIUM PRIORITY"
    else:
        priority = "🟢 LOW PRIORITY"

    return {
        "deadline_str": deadline_date.strftime("%B %d, %Y"),
        "deadline_date": deadline_date,
        "is_valid": True,
        "days_left": days_left,
        "priority": priority
    }
