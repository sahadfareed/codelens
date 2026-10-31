import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
RETRYABLE = {429, 500, 503, 504}
MAX_RETRIES = 3


def build_user_prompt(code_map: str, files: dict[str, str]) -> str:
    body = "\n\n".join(f"=== FILE: {path} ===\n{code}" for path, code in files.items())
    return f"CODE MAP:\n{code_map}\n\nSOURCE FILES:\n{body}"


def _call_model(client, model, system_prompt, user_prompt):
    """Call one model with retries + exponential backoff for temporary errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                ),
            )
        except errors.APIError as e:
            if e.code in RETRYABLE and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))   # 2s, 4s
                continue
            raise


def generate_docs(code_map: str, files: dict[str, str], project: str = "") -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to the .env file.")

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = f"PROJECT NAME (from upload): {project or 'unknown'}\n\n" + build_user_prompt(code_map, files)
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=90_000,                                   # 90s max per call
            retry_options=types.HttpRetryOptions(attempts=1), # we handle retries ourselves
        ),
    )
    models = [MODEL] + ([FALLBACK_MODEL] if FALLBACK_MODEL else [])

    last_error = None
    for model in models:
        try:
            response = _call_model(client, model, system_prompt, user_prompt)
            if not response.text or not response.text.strip():
                raise RuntimeError("The AI returned an empty response. Please regenerate.")
            return response.text
        except errors.APIError as e:
            last_error = e
            if e.code in RETRYABLE:
                continue          # try fallback model
            if e.code in (401, 403) or "API key" in str(e):
                raise RuntimeError("Invalid API key. Check GEMINI_API_KEY in .env.")
            if e.code == 404:
                raise RuntimeError(f"Model '{model}' not found. Update GEMINI_MODEL in .env.")
            raise RuntimeError(f"AI service error ({e.code}): {e.message}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Could not reach the AI service: {e}")

    if last_error is not None and last_error.code == 429:
        raise RuntimeError("Rate limit reached. Wait a minute and try again.")
    raise RuntimeError("The AI service is busy right now. Please try again in a minute.")
