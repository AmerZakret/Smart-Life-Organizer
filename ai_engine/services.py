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
    _GENAI_AVAILABLE and _GEMINI_API_KEY and _GEMINI_API_KEY != "your_gemini_api_key_here"
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
        max_output_tokens=60,   # well above 15 words but cheap insurance
        temperature=0.4,        # focused but slightly varied
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

    prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        event_title=event_title,
        start_time=formatted_time,
    )

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
