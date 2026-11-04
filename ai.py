import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()

# Priority list of free-tier compatible Gemini 3 models
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",  # Fastest, lowest congestion for Q&A
    "gemini-3.6-flash",       # Stable Flash alternative
    "gemini-3.8-flash",       # Latest flagship Flash
    "gemini-3.1-flash-lite",  # Secondary lightweight backup
]

def load_sops(sop_dir: str = "sops") -> tuple[str, list[str]]:
    """Reads all markdown SOP files and returns formatted context + list of filenames."""
    sop_path = Path(sop_dir)
    if not sop_path.exists():
        raise FileNotFoundError(f"SOP directory '{sop_dir}' not found.")

    formatted_docs = []
    loaded_files = []

    for file_path in sorted(sop_path.glob("*.md")):
        content = file_path.read_text(encoding="utf-8").strip()
        loaded_files.append(file_path.name)
        formatted_docs.append(
            f"=== DOCUMENT START: {file_path.name} ===\n"
            f"{content}\n"
            f"=== DOCUMENT END: {file_path.name} ==="
        )

    if not formatted_docs:
        raise ValueError(f"No .md files found in '{sop_dir}'.")

    return "\n\n".join(formatted_docs), loaded_files


SYSTEM_PROMPT = """You are RetailOps, an internal AI operations assistant for V-Mart store employees.
Your strict objective is to answer employee questions using ONLY the provided Standard Operating Procedure (SOP) documents.

Rules you must follow:
1. Rely exclusively on the facts directly mentioned in the supplied SOP documents. Do NOT assume, extrapolate, or use outside knowledge.
2. Keep answers concise, clear, and easy for a store employee to read quickly on the shop floor.
3. Always cite the exact document filename(s) at the end of your response on a new line using this exact format:
   Source: <filename.md>
4. If the answer is not present in the provided SOP documents, respond with:
   "I cannot find the answer to this in the current store SOPs. Please escalate this query to your Store Manager."
   Source: None
"""


def ask_sop_assistant(question: str, sop_context: str) -> str:
    """Sends the SOP context and employee question to Gemini with automatic model fallback on 503."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Check your .env file.")

    client = genai.Client(api_key=api_key)

    prompt = (
        f"Supplied Company SOP Documents:\n\n"
        f"{sop_context}\n\n"
        f"Employee Question: {question}"
    )

    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )
            return response.text.strip()
        except APIError as e:
            last_error = e
            # If the model is overloaded (503) or rate-limited (429), try the next model
            if e.code in (429, 503):
                time.sleep(0.5)
                continue
            raise e

    raise RuntimeError(f"All fallback models are currently busy. Last error: {last_error}")