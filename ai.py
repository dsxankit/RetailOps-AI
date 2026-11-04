import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Resolve base project directory regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOP_DIR = BASE_DIR / "sops"

load_dotenv(BASE_DIR / ".env")

FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
]


def load_sops(sop_dir: str | Path = DEFAULT_SOP_DIR) -> tuple[str, list[str]]:
    """Reads all markdown SOP files using absolute paths and returns context + filenames."""
    sop_path = Path(sop_dir)
    if not sop_path.is_absolute():
        sop_path = (BASE_DIR / sop_path).resolve()

    if not sop_path.exists():
        raise FileNotFoundError(f"SOP directory '{sop_path}' not found.")

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
        raise ValueError(f"No .md files found in '{sop_path}'.")

    return "\n\n".join(formatted_docs), loaded_files


SYSTEM_PROMPT = """You are RetailOps AI, an independent demonstration project showcasing an AI-powered retail operations assistant for store employees (not an official internal V-Mart tool).
Your objective is to answer store employee questions using ONLY the provided sample Standard Operating Procedure (SOP) documents.

Rules you must follow:
1. Rely exclusively on the facts directly stated in the supplied SOP documents. Do NOT assume, extrapolate, or use outside knowledge.
2. Keep answers concise, clear, and actionable for a store employee on the shop floor. Do not include raw bracketed citation numbers (such as[cite: 3]).
3. Always cite the exact SOP filename and the relevant section header at the end of your response on a new line using this exact format:
   Source: <filename.md> (Section: <Section Name>)
   (If multiple sections or files apply, list them separated by commas, e.g., Source: returns.md (Section: 1. Eligibility & Conditions, Section: 3. Damaged or Defective Products)).
4. If the answer is not present in the provided SOP documents, respond with:
   "I cannot find the answer to this in the current store SOPs. Please escalate this query to your Store Manager."
   Source: None
"""


def ask_sop_assistant(question: str, sop_context: str) -> str:
    """Sends the SOP context and employee question to Gemini and safely returns the response."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Check your .env file.")

    client = genai.Client(api_key=api_key)

    prompt = (
        f"Supplied Sample SOP Documents:\n\n"
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
            # Safely verify response.text is not None or empty before calling .strip()
            raw_text = getattr(response, "text", None)
            if not raw_text or not raw_text.strip():
                return (
                    "The AI model returned an empty response. Please try rephrasing your question.\n\n"
                    "Source: None"
                )
            return raw_text.strip()
        except APIError as e:
            last_error = e
            if e.code in (429, 503):
                time.sleep(0.5)
                continue
            raise e

    raise RuntimeError(f"All fallback models are currently busy. Last error: {last_error}")