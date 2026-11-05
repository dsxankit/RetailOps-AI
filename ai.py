import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

# Resolve base project directory regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOP_DIR = BASE_DIR / "sops"

load_dotenv(BASE_DIR / ".env")

# Defaults to your active GPU model from `ollama ps` (can be overridden in .env)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")


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
2. Distinguish carefully between actions a cashier cannot perform versus actions that are completely prohibited. If an SOP states a request (such as a return without a receipt or a damaged return) cannot be processed by cashiers and must be escalated to or approved by the Store Manager, clearly state that it requires Store Manager escalation/approval rather than saying the customer cannot return the item.
3. Keep answers concise, clear, and actionable for a store employee on the shop floor.
4. Always cite the exact SOP filename and the relevant section header at the end of your response on a new line using this exact format:
   Source: <filename.md> (Section: <Section Name>)
5. If the answer is not present in the provided SOP documents, respond with:
   "I cannot find the answer to this in the current store SOPs. Please escalate this query to your Store Manager."
   Source: None
"""


def ask_sop_assistant(question: str, sop_context: str) -> str:
    """Sends the SOP context and employee question to the local Ollama model."""
    user_prompt = (
        f"Supplied Sample SOP Documents:\n\n"
        f"{sop_context}\n\n"
        f"Employee Question: {question}"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,  # Deterministic output for strict SOP grounding
            "num_ctx": 4096,     # Matches your 4096 context window in `ollama ps`
        },
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Ollama HTTP {e.code} error (check if model '{OLLAMA_MODEL}' is pulled): {error_body}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not connect to Ollama at {OLLAMA_URL}. Make sure `ollama serve` is running."
        ) from e

    raw_text = result.get("message", {}).get("content", "")
    if not raw_text or not raw_text.strip():
        return (
            "The AI model returned an empty response. Please try rephrasing your question.\n\n"
            "Source: None"
        )

    return raw_text.strip()