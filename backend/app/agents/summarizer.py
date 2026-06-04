"""
Two lightweight LLM passes after the Strands agent:
1. Claude Sonnet  — formats the raw agent answer into recruiter-friendly markdown.
2. Claude Haiku   — generates follow-up question suggestions from the last 3 Q&A pairs.
"""
import anthropic
from app.config import get_settings

_settings = get_settings()


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=_settings.anthropic_api_key)


def format_response(raw_answer: str, user_question: str) -> str:
    """
    Claude Sonnet pass: polish the agent's raw answer into clean recruiter markdown.
    Swap → prod: add prompt caching headers for repeated summarizer calls.
    """
    resp = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=(
            "You are a recruiting analytics presenter. Take the raw data analysis below "
            "and rewrite it as clean, professional markdown for a recruiting dashboard. "
            "Rules: use **bold** for key numbers, bullet points for lists, a table if comparing >3 items. "
            "Be concise — recruiters scan, they don't read. Keep the actual numbers exact. "
            "End with a one-sentence 'Key Takeaway:' in bold."
        ),
        messages=[
            {
                "role": "user",
                "content": f"User question: {user_question}\n\nRaw agent answer:\n{raw_answer}",
            }
        ],
    )
    return resp.content[0].text


def suggest_follow_ups(qa_pairs: list[dict]) -> list[str]:
    """
    Claude Haiku pass: generate 3 contextual follow-up questions based on the last 3 Q&A pairs.
    Runs fast and cheap; does not need to see full conversation.
    """
    if not qa_pairs:
        return []

    recent = qa_pairs[-3:]
    context_lines = []
    for pair in recent:
        context_lines.append(f"Q: {pair.get('question', '')}")
        context_lines.append(f"A: {pair.get('answer', '')[:300]}...")
    context = "\n".join(context_lines)

    resp = _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=(
            "You are a recruiting analytics assistant. Based on the recent conversation, "
            "suggest exactly 3 natural follow-up questions a recruiter might ask next. "
            "Questions should be specific, data-driven, and different from what was already asked. "
            "Return ONLY the 3 questions, one per line, no numbering, no preamble."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Recent conversation:\n{context}\n\nSuggest 3 follow-up questions:",
            }
        ],
    )
    lines = [l.strip() for l in resp.content[0].text.strip().splitlines() if l.strip()]
    return lines[:3]
