import os
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def extract_deadline_and_validate(text: str) -> dict:
    """
    Extracts deadline from text. Uses local Qwen (via Ollama) as primary,
    with smart regex as fallback. Fully offline, fully open source.
    """
    # 1. Try Local Qwen via Ollama — 100% Free, Private, Open Source
    qwen_result = _try_qwen_local(text)
    if qwen_result:
        return qwen_result

    # 2. Fallback: Smart regex/keyword-based extraction (no AI needed)
    return _smart_parse_deadline(text)


def _try_qwen_local(text: str) -> dict | None:
    """Use local Qwen model via Ollama (open source, runs on your machine)."""
    url = "http://localhost:11434/api/generate"
    prompt = f"""Extract the registration deadline from the following text.
If there is no registration deadline mentioned, reply with "NONE".
If there is a deadline, format it strictly as YYYY-MM-DD.
Only output the date or NONE. No other text.

Text: {text}"""

    try:
        res = requests.post(url, json={
            "model": "qwen2.5",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }, timeout=8)

        if res.status_code == 200:
            result = res.json().get("response", "").strip()
            result = result.split("\n")[0].strip()
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
    Works without any AI model — pure Python.
    """
    text_lower = text.lower().strip()
    today = datetime.now()

    # 1) Explicit ISO date
    iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if iso_match:
        try:
            deadline = datetime.strptime(iso_match.group(1), "%Y-%m-%d")
            return _calculate_priority(deadline)
        except ValueError:
            pass

    # 2) "Month DD" or "Month DD, YYYY"
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
            if deadline < today and not month_match.group(3):
                deadline = deadline.replace(year=today.year + 1)
            return _calculate_priority(deadline)
        except ValueError:
            pass

    # 3) DD/MM/YYYY or MM/DD/YYYY
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

    # 4) Keyword heuristics
    if any(kw in text_lower for kw in ['asap', 'rolling', 'open', 'ongoing']):
        return _calculate_priority(today + timedelta(days=14))

    if 'today' in text_lower or 'tonight' in text_lower:
        return _calculate_priority(today)

    if 'tomorrow' in text_lower:
        return _calculate_priority(today + timedelta(days=1))

    if 'next week' in text_lower:
        return _calculate_priority(today + timedelta(days=7))

    if 'next month' in text_lower:
        return _calculate_priority(today + timedelta(days=30))

    days_match = re.search(r'in\s+(\d+)\s+days?', text_lower)
    if days_match:
        return _calculate_priority(today + timedelta(days=int(days_match.group(1))))

    if 'no deadline' in text_lower:
        return {"deadline_str": None, "is_valid": False, "days_left": None, "priority": "EXPIRED"}

    # Default: valid with 10 days
    return _calculate_priority(today + timedelta(days=10))


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
