"""
medgemma_provider.py
Prescription extraction via Ollama (LLaVA / MedGemma) running on Colab + ngrok.
Sends OpenAI-compatible /v1/chat/completions to the Flask proxy.
"""

import os
import base64
import time
import json
import re
from pathlib import Path
from PIL import Image, ImageEnhance
import io
import requests

import requests as http_requests

from app.schemas.prescription import PrescriptionRecord

# ── Config (all from .env) ────────────────────────────────────────────────────
LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:9001")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llava:7b")
CHAT_ENDPOINT    = f"{LLAMA_SERVER_URL}/v1/chat/completions"

MODEL_NAME    = OLLAMA_MODEL
MODEL_VERSION = "ollama"
PROMPT_TPL    = "prescription-extract-v3"

UPLOAD_DIR = Path("uploads")

SYSTEM_PROMPT = """You are an advanced medical prescription OCR and information extraction assistant.
Carefully analyze the prescription image and extract ALL available information exactly as written.

CRITICAL RULES:
1. NEVER hallucinate or invent missing information.
2. If text is partially unreadable, preserve the visible portion and add uncertainty_notes.
3. Preserve numbers, decimals, dates, units, dosage values exactly.
4. Extract ALL medications even if written diagonally, in paragraphs, or connected with arrows.
5. Preserve frequency shorthand exactly: OD, BD, TDS, QID, SOS, HS, STAT.
6. Do not convert or reformat dates.
7. route should only be filled if explicitly written — never infer.
8. confidence_score must be an integer between 0 and 100.
9. Return ONLY valid JSON — no markdown, no explanation, no comments.
10. Return null only when information is completely absent.

JSON FORMAT:
{
  "patient_name": "string or null",
  "prescriber_name": "string or null",
  "prescription_date": "string or null",
  "hospital_or_clinic": "string or null",
  "patient_age": "string or null",
  "patient_gender": "string or null",
  "diagnosis": "string or null",
  "medications": [
    {
      "medication_name": "string",
      "raw_medication_text": "string or null",
      "dosage": "string or null",
      "unit": "string or null",
      "frequency": "string or null",
      "route": "string or null",
      "duration": "string or null",
      "quantity": "string or null",
      "timing": "string or null",
      "special_instructions": "string or null",
      "uncertainty_notes": "string or null",
      "confidence_score": 85
    }
  ],
  "additional_notes": "string or null"
}"""


# ── Image preprocessing ───────────────────────────────────────────────────────

def _encode_image(file_path: Path) -> tuple[str, str]:
    with Image.open(file_path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.8)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
    return b64, "image/png"


# ── JSON parser ───────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response:\n{raw[:300]}")
    return json.loads(cleaned[start:end])


# ── Server check ──────────────────────────────────────────────────────────────

def _check_server():
    try:
        print(f"[DEBUG] Checking server at: {LLAMA_SERVER_URL}")
        r = http_requests.get(
            f"{LLAMA_SERVER_URL}/api/tags",
            timeout=5,
            headers={
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "python-requests/2.28.0"
            }
        )
        print(f"[DEBUG] Status: {r.status_code}")
        if r.status_code != 200:
            raise ConnectionError(f"Status {r.status_code}")
    except Exception as e:
        raise RuntimeError(
            f"Ollama/Flask not reachable at {LLAMA_SERVER_URL}\n"
            f"Error: {e}\n"
            "Make sure your Colab notebook is running and ngrok URL is correct in .env"
        )


# ── API call ──────────────────────────────────────────────────────────────────

def _call_llama_server(image_b64: str, mime_type: str) -> tuple[dict, int]:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            SYSTEM_PROMPT
                            + "\n\nExtract all prescription details from this image. "
                            "Return only the JSON, nothing else."
                        )
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "python-requests/2.28.0"
    }

    t_start = time.time()

    try:
        print(f"[DEBUG] Sending request to: {CHAT_ENDPOINT}")
        resp = http_requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=300
        )
        print(f"[DEBUG] Response status: {resp.status_code}")
        print(f"[DEBUG] Response body: {resp.text[:300]}")
    except http_requests.exceptions.Timeout:
        raise RuntimeError("Request timed out — model is slow, try again.")
    except Exception as e:
        raise RuntimeError(f"Request failed: {e}")

    latency_ms = int((time.time() - t_start) * 1000)

    if resp.status_code != 200:
        raise RuntimeError(f"Server error {resp.status_code}: {resp.text[:300]}")

    data     = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    extracted = _parse_json(raw_text)
    return extracted, latency_ms


# ── Main entry point ──────────────────────────────────────────────────────────

def medgemma_extract(file_name: str, record_id: str) -> PrescriptionRecord:
    _check_server()

    file_path = UPLOAD_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    image_b64, mime_type = _encode_image(file_path)
    extracted_data, latency_ms = _call_llama_server(image_b64, mime_type)

    if "medications" not in extracted_data:
        extracted_data["medications"] = []

    return PrescriptionRecord(
        record_id=record_id,
        source_file=file_name,
        method="ollama-vision",
        extracted=extracted_data,
        review={
            "status": "pending",
            "reviewer_notes": None,
            "reviewed_at": None
        },
        run_metadata={
            "model_name":     MODEL_NAME,
            "model_version":  MODEL_VERSION,
            "runtime":        "ollama-colab-ngrok",
            "latency_ms":     latency_ms,
            "prompt_template": PROMPT_TPL
        }
    )