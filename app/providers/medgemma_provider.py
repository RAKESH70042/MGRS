"""
MedGemma 4B Local Provider — llama.cpp server
Level 1 + Level 2 improvements:
- Full prompt with complete JSON schema
- Image preprocessing (resize + contrast + sharpness)
"""

import os
import base64
import time
import json
import re
from pathlib import Path
from PIL import Image, ImageEnhance
import io

import requests as http_requests

from app.schemas.prescription import PrescriptionRecord

LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:8080")
CHAT_ENDPOINT    = f"{LLAMA_SERVER_URL}/v1/chat/completions"

MODEL_NAME    = "medgemma-4b-it"
MODEL_VERSION = "Q4_K_M"
PROMPT_TPL    = "prescription-extract-v2"

UPLOAD_DIR = Path("uploads")

SYSTEM_PROMPT = """You are an advanced medical prescription OCR and information extraction assistant.
Your task is to carefully analyze a medical prescription image and extract ALL available information exactly as written.

The prescription may contain:
- handwritten text
- cursive writing
- printed/computer-generated text
- OCR noise
- medical abbreviations
- special symbols
- incomplete words
- overlapping text
- stamps and signatures

You must prioritize COMPLETE extraction over clean formatting.

CRITICAL RULES:
1. NEVER hallucinate or invent missing information.
2. NEVER skip unclear text.
3. If text is partially unreadable:
   - preserve the visible portion
   - add uncertainty_notes
4. Preserve:
   - numbers, decimals, dates, timings
   - units, dosage values
   - symbols (#, /, -, +, :, %, mg, ml, IU, OD, BD, SOS, HS, etc.)
5. Extract ALL medications, even if:
   - separated across lines
   - written diagonally
   - connected with arrows
   - written below "Sig:"
   - grouped in paragraphs
6. Associate nearby dosage/frequency/duration instructions with the correct medication.
7. Do not merge separate medications into one entry.
8. Maintain exact spelling from prescription whenever possible.
9. If confidence is low, preserve original OCR text instead of correcting aggressively.
10. Return null only when information is completely absent.
11. Ignore unrelated license numbers (Lic No, PTR No, S2 No) unless part of medication instructions.
12. Physician signature or stamped doctor name should be extracted as prescriber_name.
13. Preserve all quantities exactly as written: #10, Qty:20, x30, 1+1+1, 0-1-0, 1/2
14. Preserve frequency exactly in shorthand: OD, BD, TDS, QID, SOS, HS, STAT
15. Do not convert or reformat dates — preserve exactly as written on the prescription.
16. route should only be filled if explicitly written — never infer or guess it.
17. confidence_score must be an integer between 0 and 100.

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON
- No markdown, no explanation, no comments
- JSON must always be syntactically valid

JSON FORMAT:
{
  "patient_name": "string or null",
  "prescriber_name": "string or null",
  "prescription_date": "string or null (preserve exactly as written)",
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


def _encode_image(file_path: Path) -> tuple[str, str]:
    """
    Load image with Pillow, preprocess for better OCR quality, return base64 PNG.
    - Converts to RGB
    - Upscales small images (MedGemma reads better at higher resolution)
    - Boosts contrast and sharpness for faded/scanned prescriptions
    """
    with Image.open(file_path) as img:
        # Strip alpha channel / palette modes
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Upscale if image is too small
        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS
            )

        # Boost contrast for faded/scanned prescriptions
        img = ImageEnhance.Contrast(img).enhance(1.8)

        # Boost sharpness for blurry or low-res images
        img = ImageEnhance.Sharpness(img).enhance(2.0)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")

    return b64, "image/png"


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response:\n{raw}")
    return json.loads(cleaned[start:end])


def _check_server():
    """Check that the llama.cpp server is up and reachable."""
    try:
        r = http_requests.get(f"{LLAMA_SERVER_URL}/health", timeout=3)
        if r.status_code != 200:
            raise ConnectionError()
    except Exception:
        raise RuntimeError(
            f"llama.cpp server not running at {LLAMA_SERVER_URL}\n"
            "Start it with:\n"
            r"  llama.cpp\llama-server.exe -m models\google_medgemma-4b-it-Q4_K_M.gguf "
            r"--mmproj models\mmproj-medgemma-4b-it-F16.gguf --port 8080 --ctx-size 4096 -ngl 0 --threads 6"
        )


def _call_llama_server(image_b64: str, mime_type: str) -> tuple[dict, int]:

    payload = {
        "model": "medgemma",
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
                            SYSTEM_PROMPT + "\n\n"
                            "Extract all prescription details from this image. "
                            "Return only the JSON, nothing else."
                        )
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "stream": False
    }

    headers = {"Content-Type": "application/json"}
    t_start = time.time()

    try:
        resp = http_requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=300
        )
    except http_requests.exceptions.Timeout:
        raise RuntimeError("Request timed out — model is slow, try again.")

    latency_ms = int((time.time() - t_start) * 1000)

    if resp.status_code != 200:
        raise RuntimeError(
            f"llama.cpp error {resp.status_code}: {resp.text[:500]}"
        )

    data     = resp.json()
    raw_text = data["choices"][0]["message"]["content"]

    extracted = _parse_json(raw_text)
    return extracted, latency_ms


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
        method="medgemma",
        extracted=extracted_data,
        review={
            "status": "pending",
            "reviewer_notes": None,
            "reviewed_at": None
        },
        run_metadata={
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "runtime": "llama-cpp-local",
            "latency_ms": latency_ms,
            "prompt_template": PROMPT_TPL
        }
    )