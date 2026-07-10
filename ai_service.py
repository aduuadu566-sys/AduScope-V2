"""
AduScope - AI Service Layer
All communication with the AI model lives here, isolated from the UI so it
can be swapped, mocked, or unit-tested independently.

Uses OpenRouter (https://openrouter.ai) — an OpenAI-compatible gateway with a
genuinely free tier (no credit card, no regional restrictions, since requests
are routed through OpenRouter's own servers).
"""

import json
import datetime
import requests

from config import OPENROUTER_API_KEY, AI_MODEL, MAX_TOKENS

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def _generate(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    """Low-level helper: one call to OpenRouter's chat completions endpoint,
    returns the raw text reply."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Export it as an environment "
            "variable before running the app. Get a free key at "
            "https://openrouter.ai"
        )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": AI_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    resp = requests.post(_ENDPOINT, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def _ask_json(system_prompt: str, user_prompt: str) -> dict:
    """Helper: call the model, force JSON-only output, parse and return a
    dict. Retries once with a stricter reminder if the first parse fails."""
    json_system = system_prompt + "\nReturn ONLY raw JSON, no markdown fences, no prose."
    raw = _generate(json_system, user_prompt, MAX_TOKENS)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raw = _generate(
                json_system + "\nCRITICAL: Reply with ONLY the raw JSON object. "
                "No markdown fences, no preamble, no explanation whatsoever.",
                user_prompt, MAX_TOKENS,
            )
            cleaned = raw.strip().strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            return json.loads(cleaned)


# ---------------------------------------------------------------------------
# 1. First question — unique every single time, deliberately weighty
# ---------------------------------------------------------------------------
def generate_first_question(name: str, language_code: str, language_name: str) -> str:
    now = datetime.datetime.now()
    system = (
        "You are AduScope, a serious, perceptive talent-discovery interviewer. "
        "Generate exactly ONE opening question that is deliberately weighty, "
        "serious, and thought-provoking — not casual small talk. It must be "
        "open-ended (absolutely no multiple choice), impossible to answer with "
        "a single word, and should immediately signal that this interview is "
        "meaningful and worth taking seriously. "
        f"Respond ONLY in this language: {language_name} ({language_code}). "
        "Reply with ONLY the question text, nothing else — no JSON, no quotes."
    )
    user = (
        f"User name: {name}\n"
        f"Local time right now: {now.strftime('%A %H:%M')}\n"
        "Use the name, the time of day, and creativity so that no two users "
        "ever get the same opening question, while keeping the serious, "
        "weighty tone. Write the single opening question now."
    )
    return _generate(system, user, 300)


# ---------------------------------------------------------------------------
# 1b. Warm, personalized welcome message (replaces the old hardcoded lines)
# ---------------------------------------------------------------------------
def generate_welcome_message(name: str, language_name: str) -> str:
    system = (
        "You are AduScope, a warm talent-discovery app. Write a short, "
        "beautifully-worded welcome (2-3 sentences) for a user who just "
        "entered their name. Mention that AduScope exists to discover their "
        "unique, genuine talent through a short interview. Make it feel "
        f"premium and sincere, not generic. Respond ONLY in {language_name}. "
        "Reply with ONLY the welcome text, nothing else."
    )
    user = f"User's name: {name}"
    return _generate(system, user, 250)


# ---------------------------------------------------------------------------
# 1c. Thank-you / sharing message shown near the end of the flow
# ---------------------------------------------------------------------------
def generate_thankyou_message(name: str, language_name: str) -> str:
    system = (
        "You are AduScope. Write a short, warm closing message (2-4 "
        "sentences) thanking the user by name for trusting AduScope to "
        "discover their talent. Invite them to share the app with a friend "
        "or family member so the two of them can compare talents inside the "
        f"app. Respond ONLY in {language_name}. Reply with ONLY the message "
        "text, nothing else."
    )
    user = f"User's name: {name}"
    return _generate(system, user, 250)


# ---------------------------------------------------------------------------
# 1d. Translate the small set of fixed UI labels into the chosen language
# ---------------------------------------------------------------------------
_UI_KEYS = [
    "your_name", "continue", "begin", "your_answer", "submit", "save_entry",
    "restart", "share_copy_code", "daily_journal", "compare_with_friend",
    "back", "settings", "music_on", "music_off", "change_language",
    "close_app", "restart_app", "press_instruction", "write_reflection", "day",
]


def translate_ui_strings(language_name: str) -> dict:
    """
    Returns a dict mapping each key in _UI_KEYS to a short UI label written
    naturally in the target language, so every word in the app (not just
    AI-generated content) matches the user's chosen language.
    """
    system = (
        "Translate this exact list of short UI button/label keys into "
        f"{language_name}, as natural short UI text a mobile app would use: "
        f"{_UI_KEYS}. Return STRICT JSON only: an object with each key from "
        "the list mapped to its short translated label (2-4 words max each). "
        "No markdown, no prose outside the JSON."
    )
    user = "Translate now."
    result = _ask_json(system, user)
    # Fallback: fill anything missing with the English key itself
    for k in _UI_KEYS:
        if k not in result or not result[k]:
            result[k] = k.replace("_", " ").title()
    return result


# ---------------------------------------------------------------------------
# 2. Grade an answer + decide next question's difficulty
# ---------------------------------------------------------------------------
def grade_answer(question: str, answer: str, language_name: str) -> dict:
    """
    Returns:
    {
        "on_topic": bool,
        "score": int (1-10),
        "level": "low" | "medium" | "high",
        "reasoning": short internal note (not shown to user),
        "signal": short string describing the talent signal detected,
        "mood_emoji": single emoji capturing the tone of the writing
    }
    """
    system = (
        "You are an expert psychometric evaluator for a talent-discovery app. "
        "Analyze the user's answer for: relevance to the question, vocabulary "
        "richness, emotional maturity, logical structure, and creativity. Also "
        "read the emotional tone/energy of the writing itself. "
        "Return STRICT JSON only, matching this schema exactly:\n"
        '{"on_topic": true/false, "score": 1-10, "level": "low|medium|high", '
        '"reasoning": "one short sentence", "signal": "one short phrase naming '
        'a possible talent/strength this answer hints at", '
        '"mood_emoji": "one single emoji capturing the tone of the writing"}\n'
        "No markdown, no prose outside the JSON."
    )
    user = f"Question ({language_name}): {question}\nUser's answer: {answer}"
    return _ask_json(system, user)


# ---------------------------------------------------------------------------
# 3. Next question, adapted to previous performance
# ---------------------------------------------------------------------------
def generate_next_question(history: list, language_name: str, difficulty_level: str) -> str:
    """
    history: list of {"question": str, "answer": str, "level": str}
    difficulty_level: "low" | "medium" | "high" — how hard the NEXT question
    should be, based on the grading of the previous answer.
    """
    system = (
        "You are AduScope, continuing an adaptive talent-discovery interview. "
        f"Respond ONLY in {language_name}. Reply with ONLY the next question "
        "text — open-ended, no multiple choice, no numbering, no quotes."
    )
    transcript = "\n".join(
        f"Q: {h['question']}\nA: {h['answer']}" for h in history
    )
    user = (
        f"Interview so far:\n{transcript}\n\n"
        f"The next question should be {difficulty_level} difficulty relative "
        "to the last one, should not repeat any earlier topic, and should dig "
        "deeper into whatever unique strength is emerging. Write it now."
    )
    return _generate(system, user, 300)


# ---------------------------------------------------------------------------
# 4. Final talent verdict + certificate + roadmap
# ---------------------------------------------------------------------------
def generate_final_result(name: str, history: list, language_name: str) -> dict:
    """
    Returns:
    {
        "talent_title": str,
        "talent_summary": str,
        "personality_analysis": str,
        "roadmap": str,
        "certificate_line": str
    }
    """
    system = (
        "You are AduScope's chief talent analyst. Based on a full 10-question "
        "adaptive interview transcript, identify the person's single strongest "
        "unique talent. Be specific and genuine — avoid generic flattery. "
        f"Respond ONLY in {language_name}. Return STRICT JSON only:\n"
        '{"talent_title": "...", "talent_summary": "...", '
        '"personality_analysis": "...", "roadmap": "...", '
        '"certificate_line": "..."}\n'
        "No markdown fences, no prose outside the JSON."
    )
    transcript = "\n".join(
        f"Q{i+1}: {h['question']}\nA{i+1}: {h['answer']} (score {h.get('score','?')})"
        for i, h in enumerate(history)
    )
    user = f"Candidate name: {name}\n\nFull transcript:\n{transcript}"
    return _ask_json(system, user)


# ---------------------------------------------------------------------------
# 5. Talent Twin — compare to a well-known figure (folded into result screen)
# ---------------------------------------------------------------------------
def generate_talent_twin(talent_title: str, talent_summary: str, language_name: str) -> dict:
    """Returns: {"twin_name": "...", "twin_reason": "one or two sentences"}"""
    system = (
        "You help people relate their newly-discovered talent to a well-known "
        "public figure (historical or contemporary) who is famous for a similar "
        "strength. Pick someone genuinely fitting, not generic (avoid always "
        "picking Einstein/Steve Jobs unless truly apt). "
        f"Respond ONLY in {language_name}. Return STRICT JSON only: "
        '{"twin_name": "Full Name", "twin_reason": "1-2 sentence explanation"}'
    )
    user = f"Talent: {talent_title}\nSummary: {talent_summary}"
    return _ask_json(system, user)


# ---------------------------------------------------------------------------
# 6. Tone / mood analysis for a single answer (lightweight, no audio needed)
# ---------------------------------------------------------------------------
def analyze_tone(answer: str) -> dict:
    """Returns: {"emoji": "single emoji", "mood": "one word"}"""
    system = (
        "Read the emotional tone/energy of this short piece of writing. "
        "Return STRICT JSON only: "
        '{"emoji": "one single emoji that captures the tone", "mood": "one word mood label"}'
    )
    return _ask_json(system, answer)


# ---------------------------------------------------------------------------
# 7. Badge spec — a code-drawn badge, no image-generation API needed
# ---------------------------------------------------------------------------
_VALID_ICONS = [
    "psychology", "auto_awesome", "star", "military_tech", "workspace_premium"
]

