"""
report_generator.py
Sends the full consultation transcript to MedGemma and gets back
a structured JSON medical report.
"""

import os
import json
import re
import requests

LLAMA_SERVER_URL = os.getenv("LLAMA_SERVER_URL", "http://localhost:8080")
CHAT_ENDPOINT    = f"{LLAMA_SERVER_URL}/v1/chat/completions"

REPORT_PROMPT = """You are an expert medical scribe AI.
You will be given a full doctor-patient consultation transcript with speaker labels.
Your job is to generate a complete, accurate structured medical report.

CRITICAL RULES:
1. Only use information explicitly stated in the transcript.
2. Never hallucinate symptoms, diagnoses, or medications.
3. If information is absent, use null.
4. Return ONLY valid JSON — no markdown, no explanation.

JSON FORMAT:
{
  "patient_complaints": "string or null",
  "symptoms": "string or null",
  "doctor_observations": "string or null",
  "diagnosis": "string or null",
  "prescribed_medicines": [
    {
      "medication_name": "string",
      "dosage": "string or null",
      "unit": "string or null",
      "frequency": "string or null",
      "duration": "string or null",
      "special_instructions": "string or null"
    }
  ],
  "tests_recommended": "string or null",
  "follow_up_instructions": "string or null",
  "treatment_plan": "string or null",
  "important_notes": "string or null",
  "icd10_suggestions": "string or null",
  "soap_note": "string or null"
}"""


def _format_transcript(turns: list) -> str:
    lines = []
    for turn in turns:
        speaker = turn.get("speaker", "Unknown")
        text    = turn.get("text", "")
        ts      = turn.get("timestamp", 0)
        lines.append(f"[{ts:.1f}s] {speaker}: {text}")
    return "\n".join(lines)


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON in response: {raw[:300]}")
    return json.loads(cleaned[start:end])


def generate_report(turns: list) -> dict:
    """
    turns: list of dicts with keys: speaker, text, timestamp
    Returns: structured report dict
    """
    transcript_text = _format_transcript(turns)

    payload = {
        "model": "medgemma",
        "messages": [
            {
                "role": "user",
                "content": (
                    REPORT_PROMPT
                    + "\n\nCONSULTATION TRANSCRIPT:\n"
                    + transcript_text
                    + "\n\nGenerate the structured report JSON now."
                )
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
        "stream": False
    }

    try:
        resp = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("MedGemma timed out generating report.")

    if resp.status_code != 200:
        raise RuntimeError(f"MedGemma error {resp.status_code}: {resp.text[:300]}")

    raw = resp.json()["choices"][0]["message"]["content"]
    return _parse_json(raw)


def generate_report_mock(turns: list) -> dict:
    """Returns a fake report for testing without MedGemma."""
    return {
        "patient_complaints": "Fever and sore throat for 3 days",
        "symptoms": "High temperature (38.5°C), difficulty swallowing, fatigue",
        "doctor_observations": "Throat red and inflamed, no tonsil exudate",
        "diagnosis": "Viral pharyngitis",
        "prescribed_medicines": [
            {
                "medication_name": "Paracetamol",
                "dosage": "500",
                "unit": "mg",
                "frequency": "TDS",
                "duration": "5 days",
                "special_instructions": "After food"
            }
        ],
        "tests_recommended": "Throat swab if no improvement in 48 hours",
        "follow_up_instructions": "Return in 1 week or sooner if fever worsens",
        "treatment_plan": "Symptomatic management, rest, hydration",
        "important_notes": "Avoid cold drinks",
        "icd10_suggestions": "J02.9 — Acute pharyngitis, unspecified",
        "soap_note": (
            "S: Patient reports 3-day fever and sore throat.\n"
            "O: Temp 38.5°C, pharynx erythematous.\n"
            "A: Viral pharyngitis.\n"
            "P: Paracetamol 500mg TDS x5 days, follow up 1 week."
        )
    }