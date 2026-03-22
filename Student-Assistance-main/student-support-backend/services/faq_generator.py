import json
import re
from datetime import datetime
from pathlib import Path

from database import chat_logs_collection, intents_collection


BASE_DIR = Path(__file__).resolve().parent.parent
INTENTS_FILE = BASE_DIR / "intents.json"


def _normalize_text(value):
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _load_intents():
    try:
        rows = list(intents_collection.find({}, {"_id": 0, "tag": 1, "intent": 1, "patterns": 1, "responses": 1}))
        if rows:
            return rows
    except Exception:
        pass

    try:
        with INTENTS_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
            return payload.get("intents", [])
    except Exception:
        return []


def _serialize_dt(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def generate_faq_items(limit=10):
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    seen_questions = set()
    items = []

    intents = _load_intents()
    for intent in intents:
        responses = [r for r in (intent.get("responses") or []) if isinstance(r, str) and r.strip()]
        raw_patterns = intent.get("patterns") or intent.get("text") or []
        patterns = [p for p in raw_patterns if isinstance(p, str) and p.strip()]
        if not responses or not patterns:
            continue

        answer = responses[0].strip()
        tag = (intent.get("tag") or intent.get("intent") or "general").strip()

        for question in patterns[:2]:
            normalized = _normalize_text(question)
            if not normalized or normalized in seen_questions:
                continue
            seen_questions.add(normalized)
            items.append(
                {
                    "question": question.strip(),
                    "answer": answer,
                    "category": tag,
                    "source": "intent_catalog",
                    "count": None,
                    "last_seen": None,
                    "status": "answered",
                }
            )
            if len(items) >= limit:
                return items

    # Add most frequent answered user questions from chat logs.
    try:
        pipeline = [
            {"$match": {"message": {"$type": "string", "$ne": ""}, "response": {"$type": "string", "$ne": ""}}},
            {
                "$project": {
                    "q": {"$trim": {"input": "$message"}},
                    "a": {"$trim": {"input": "$response"}},
                    "timestamp": 1,
                }
            },
            {"$match": {"q": {"$ne": ""}, "a": {"$ne": ""}}},
            {
                "$group": {
                    "_id": {"q": {"$toLower": "$q"}, "a": "$a"},
                    "count": {"$sum": 1},
                    "last_seen": {"$max": "$timestamp"},
                    "question": {"$first": "$q"},
                }
            },
            {"$sort": {"count": -1, "last_seen": -1}},
            {"$limit": 100},
        ]
        rows = list(chat_logs_collection.aggregate(pipeline))
        for row in rows:
            question = (row.get("question") or "").strip()
            answer = ((row.get("_id") or {}).get("a") or "").strip()
            normalized = _normalize_text(question)
            if not question or not answer or not normalized or normalized in seen_questions:
                continue
            seen_questions.add(normalized)
            items.append(
                {
                    "question": question,
                    "answer": answer,
                    "category": "student_queries",
                    "source": "chat_logs",
                    "count": int(row.get("count", 0)),
                    "last_seen": _serialize_dt(row.get("last_seen")),
                    "status": "answered",
                }
            )
            if len(items) >= limit:
                break
    except Exception:
        pass

    return items[:limit]
