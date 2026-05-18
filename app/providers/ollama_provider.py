"""
ollama_provider.py - NOT USED (kept as fallback)
Main provider is medgemma_provider.py via Flask proxy.
"""

import os
import json
import re
import time
import base64
import io
from pathlib import Path

import requests as http_requests
from PIL import Image, ImageEnhance

from app.schemas.prescription import PrescriptionRecord

LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:11434")
OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llava:7b")
CHAT_ENDPOINT    = f"{LLAMA_SERVER_URL}/api/chat"

UPLOAD_DIR = Path("uploads")

SYSTEM_PROMPT = """You are a medical prescription OCR and information extraction assistant.
Analyze the prescription and extract all available information.

CRITICAL RULES:
1. NEVER hallucinate or invent missing information.
2. Return ONLY valid JSON — no markdown, no explanation, no comments.
3. Use null when information is absent.
4. Preserve exact spelling, dosage values, and frequency shorthand (OD, BD, TDS, QID, SOS).

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


def _encode_image(file_path: Path) -> str:
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
        return base64.b64encode(buf.read()).decode("utf-8")


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response:\n{raw[:300]}")
    return json.loads(cleaned[start:end])


def _check_server():
    try:
        r = http_requests.get(
            f"{LLAMA_SERVER_URL}/api/tags",
            timeout=5,
            headers={
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "python-requests/2.28.0"
            }
        )
        if r.status_code != 200:
            raise ConnectionError(f"Status {r.status_code}")
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(OLLAMA_MODEL in m for m in models):
            raise RuntimeError(
                f"Model '{OLLAMA_MODEL}' not found in Ollama.\n"
                f"Available: {models}"
            )
    except Exception as e:
        raise RuntimeError(
            f"Ollama not reachable at {LLAMA_SERVER_URL}\n"
            f"Error: {e}"
        )


def _call_ollama(image_b64: str) -> tuple[dict, int]:
    vision_models = {"llava", "llava-phi3", "moondream", "bakllava", "medgemma"}
    has_vision = any(v in OLLAMA_MODEL.lower() for v in vision_models)

    if has_vision:
        content = [
            {"type": "text", "text": SYSTEM_PROMPT + "\n\nExtract all prescription details. Return only JSON."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        ]
    else:
        content = SYSTEM_PROMPT + "\n\nNo image available. Return empty prescription JSON with null fields."

    payload = {
        "model":  OLLAMA_MODEL,
        "stream": False,
        "messages": [{"role": "user", "content": content}],
        "options": {"temperature": 0.1}
    }

    t_start = time.time()
    try:
        resp = http_requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "python-requests/2.28.0"
            },
            timeout=300
        )
    except http_requests.exceptions.Timeout:
        raise RuntimeError("Ollama timed out — try again.")

    latency_ms = int((time.time() - t_start) * 1000)

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text[:300]}")

    raw_text = resp.json()["message"]["content"]
    extracted = _parse_json(raw_text)
    return extracted, latency_ms


def ollama_extract(file_name: str, record_id: str) -> PrescriptionRecord:
    _check_server()

    file_path = UPLOAD_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    image_b64 = _encode_image(file_path)
    extracted_data, latency_ms = _call_ollama(image_b64)

    if "medications" not in extracted_data:
        extracted_data["medications"] = []

    return PrescriptionRecord(
        record_id=record_id,
        source_file=file_name,
        method="ollama",
        extracted=extracted_data,
        review={"status": "pending", "reviewer_notes": None, "reviewed_at": None},
        run_metadata={
            "model_name":      OLLAMA_MODEL,
            "model_version":   "ollama",
            "runtime":         "ollama-remote",
            "latency_ms":      latency_ms,
            "prompt_template": "prescription-extract-ollama-v1"
        }
    )