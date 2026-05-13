"""
ai_engine/services.py
─────────────────────
Gemini API utility layer for Smart Life Organizer.

Uses the current `google-genai` SDK (google.genai), which replaced the
deprecated `google-generativeai` package.

Public API
──────────
    generate_event_tip(event_title: str, start_time: datetime) -> str | None
        Calls Gemini 1.5 Flash with the project-mandated system prompt and
        returns a single ≤15-word actionable tip string, or None on any failure.
        Never raises — callers should treat None as "tip unavailable".
"""

import os
import logging

logger = logging.getLogger(__name__)

# Try to import the google/genai SDK; if it's not installed, degrade gracefully.
try:
    from google import genai
    from google.genai import types as genai_types

    _GENAI_AVAILABLE = True
except Exception:
    genai = None
    genai_types = None
    _GENAI_AVAILABLE = False
    logger.warning("google.genai SDK not available; AI tip generation disabled.")

# ── Gemini client initialisation ──────────────────────────────────────────────
_GEMINI_API_KEY: str | None = os.environ.get("GEMINI_API_KEY", "")

_CLIENT_READY: bool = bool(
    _GENAI_AVAILABLE
    and _GEMINI_API_KEY
    and _GEMINI_API_KEY != "your_gemini_api_key_here"
)

if _CLIENT_READY:
    _client = genai.Client(api_key=_GEMINI_API_KEY)
    logger.info("Gemini client initialised successfully.")
else:
    _client = None
    if _GENAI_AVAILABLE:
        logger.warning(
            "GEMINI_API_KEY is not set or is still the placeholder value. "
            "AI tips will be disabled until a valid key is provided in .env"
        )

# ── Model + generation settings ───────────────────────────────────────────────
_MODEL_NAME = "gemini-flash-latest"

if _GENAI_AVAILABLE and genai_types is not None:
    _GENERATE_CONTENT_CONFIG = genai_types.GenerateContentConfig(
        max_output_tokens=60,  # well above 15 words but cheap insurance
        temperature=0.4,  # focused but slightly varied
    )
else:
    _GENERATE_CONTENT_CONFIG = None

# ── System prompt (exact spec from plan.txt §5) ───────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = (
    "You are a sophisticated personal productivity assistant. "
    "The user has scheduled an event: '{event_title}' on {start_time}. "
    "Provide one high-quality, insightful, and practical tip to help the user prepare or perform better. "
    "Be specific to the context of the event title. Avoid generic advice like 'be on time'. "
    "Keep your response between 15 and 25 words. Do not use markdown or conversational filler."
)


def generate_event_tip(event_title: str, start_time) -> str | None:
    """
    Call Gemini 1.5 Flash to produce a ≤15-word preparation tip for an event.

    Parameters
    ----------
    event_title : str
        The title of the event (e.g. "Team standup").
    start_time : datetime
        The event's start datetime (used in the prompt for context).

    Returns
    -------
    str | None
        The tip text, or None if the API key is missing / any error occurs.
    """
    if not _CLIENT_READY or _client is None:
        logger.debug("Skipping AI tip generation: client not ready.")
        return None

    # Format start_time as a human-readable string for the prompt
    try:
        formatted_time = start_time.strftime("%A, %B %d at %I:%M %p")
    except AttributeError:
        formatted_time = str(start_time)

    try:
        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=f"Event: '{event_title}' on {formatted_time}",
            config=genai_types.GenerateContentConfig(
                system_instruction="You are a sophisticated productivity assistant. Provide one insightful, specific, and practical preparation tip for the given event. Avoid generic advice. Respond with exactly one helpful sentence.",
                max_output_tokens=1000,
                temperature=0.8,
            ),
        )
        tip = response.text.strip() if response.text else None
        if tip:
            logger.info("AI tip generated for event '%s': %s", event_title, tip)
        return tip

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Gemini API call failed for event '%s': %s",
            event_title,
            exc,
        )
        return None

def generate_dashboard_insight(username: str, events: list, habits: list, tone: str, pending_tasks_count: int = 0) -> str | None:
    """
    Call Gemini 1.5 Flash to produce a personalized, contextual dashboard tip.
    """
    if not _CLIENT_READY or _client is None:
        logger.debug("Skipping AI tip generation: client not ready.")
        return None

    events_context = []
    for e in events:
        try:
            time_str = e.start_time.strftime('%a %I:%M %p')
        except AttributeError:
            time_str = str(e.start_time)
        events_context.append(f"'{e.title}' at {time_str}")
    
    habits_context = []
    for h in habits:
        if h.current_streak > 0:
            habits_context.append(f"'{h.name}' ({h.current_streak} day streak)")

    prompt_content = (
        f"User: {username}\n"
        f"Pending Tasks: {pending_tasks_count}\n"
        f"Upcoming Events (next 48h): {', '.join(events_context) if events_context else 'None'}\n"
        f"Active Habit Streaks: {', '.join(habits_context) if habits_context else 'None'}"
    )
    
    tone_instruction = "Be highly motivational and enthusiastic."
    if tone == "direct":
        tone_instruction = "Be direct, concise, and professional."
    elif tone == "funny":
        tone_instruction = "Be humorous and witty."

    system_instruction = (
        f"You are a sophisticated productivity assistant for {username}, a software engineering student. "
        "Review their pending tasks, upcoming events, and habit streaks, then provide ONE short, highly personalized sentence of advice or encouragement. "
        "Reference specific data when possible (e.g. mention an event title or a streak count). "
        f"{tone_instruction} "
        "Do not use filler, markdown, or greetings. Keep it under 30 words."
    )

    try:
        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=80,
                temperature=0.7,
            ),
        )
        return response.text.strip() if response.text else None
    except Exception as exc:
        logger.error("Gemini API call failed for dashboard insight: %s", exc)
        return None


def chat_with_data(username: str, data_json: str, user_question: str) -> str | None:
    """
    Chat with the user's productivity data using Gemini.

    Parameters
    ----------
    username : str
        The display name of the user (for personalisation).
    data_json : str
        A JSON string summarising the user's recent tasks, habits, and
        pomodoro sessions.
    user_question : str
        The natural-language question asked by the user.

    Returns
    -------
    str | None
        The AI-generated answer, or None on failure.
    """
    if not _CLIENT_READY or _client is None:
        logger.debug("Skipping AI chat: client not ready.")
        return None

    system_instruction = (
        f"You are a productivity assistant for {username}. "
        "Based on the provided JSON data of his tasks, habits, and pomodoro sessions, "
        "answer his questions accurately. Be concise and reference specific data points "
        "when possible. Respond in a warm but professional tone. "
        "Keep responses under 100 words. Do not use markdown formatting."
    )

    prompt_content = (
        f"Here is my recent productivity data (last 7 days):\n"
        f"{data_json}\n\n"
        f"My question: {user_question}"
    )

    try:
        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=300,
                temperature=0.5,
            ),
        )
        answer = response.text.strip() if response.text else None
        if answer:
            logger.info("AI chat response generated for user '%s'.", username)
        return answer
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini API chat call failed: %s", exc)
        return None


def generate_roadmap(username: str, target_goal: str) -> dict | None:
    """
    Ask Gemini to break a target goal into 5 specific tasks and 2 daily habits.

    Parameters
    ----------
    username : str
        The display name of the user.
    target_goal : str
        The goal to decompose (e.g. "Learn Flutter").

    Returns
    -------
    dict | None
        A dict with keys ``"tasks"`` (list of 5 strings) and ``"habits"``
        (list of 2 strings), or None on failure.
    """
    if not _CLIENT_READY or _client is None:
        logger.debug("Skipping roadmap generation: client not ready.")
        return None

    system_instruction = (
        f"You are a productivity coach for {username}. "
        "When given a goal, return a JSON object with exactly 5 actionable tasks "
        "and 2 daily habits. Keep each item under 10 words. "
        "Use this exact JSON schema: "
        '{"tasks":["t1","t2","t3","t4","t5"],"habits":["h1","h2"]}'
    )

    try:
        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=f"My goal: {target_goal}",
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=1024,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )
        raw = response.text.strip() if response.text else None
        if not raw:
            return None

        # Strip markdown code fences if Gemini wraps the JSON
        import re
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        import json as _json
        result = _json.loads(cleaned)

        # Validate structure
        if (
            isinstance(result, dict)
            and isinstance(result.get("tasks"), list)
            and isinstance(result.get("habits"), list)
            and len(result["tasks"]) >= 1
            and len(result["habits"]) >= 1
        ):
            logger.info(
                "Roadmap generated for goal '%s': %d tasks, %d habits.",
                target_goal,
                len(result["tasks"]),
                len(result["habits"]),
            )
            return result

        logger.warning("Roadmap response had unexpected structure: %s", raw)
        return None

    except (_json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse roadmap JSON: %s — raw: %s", exc, raw)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini roadmap API call failed: %s", exc)
        return None

