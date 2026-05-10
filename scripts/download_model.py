"""
MedGemma GGUF Model Downloader (fixed repo name)
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN  = os.getenv("HF_TOKEN", "")
MODEL_DIR = Path("models")

FILES = [
    {
        "repo": "bartowski/google_medgemma-4b-it-GGUF",
        "file": "google_medgemma-4b-it-Q4_K_M.gguf",
        "desc": "Main model (~2.7 GB)"
    },
    {
        "repo": "kelkalot/medgemma-4b-it-GGUF",
        "file": "mmproj-medgemma-4b-it-F16.gguf",
        "desc": "Vision projector — required for image reading (~300 MB)"
    }
]


def download_file(repo, filename, desc):
    url  = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    dest = MODEL_DIR / filename

    if dest.exists():
        print(f"✅ Already exists: {filename}")
        return

    print(f"\n⬇️  Downloading {desc}")
    print(f"    {filename}")

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    with requests.get(url, headers=headers, stream=True) as r:
        if r.status_code == 401:
            print("❌ Bad token — check HF_TOKEN in .env")
            sys.exit(1)
        if r.status_code == 403:
            print("❌ Accept license at https://huggingface.co/google/medgemma-4b-it")
            sys.exit(1)
        r.raise_for_status()

        total      = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct     = downloaded / total * 100
                    done_mb = downloaded / (1024**2)
                    tot_mb  = total / (1024**2)
                    print(f"\r    {pct:.1f}%  {done_mb:.0f} / {tot_mb:.0f} MB", end="", flush=True)

    print(f"\n✅ Done: {filename}")


def main():
    if not HF_TOKEN:
        print("❌ HF_TOKEN not set in .env")
        sys.exit(1)

    MODEL_DIR.mkdir(exist_ok=True)

    for f in FILES:
        download_file(f["repo"], f["file"], f["desc"])

    print("\n✅ All files downloaded!")
    print("\nNext — start the server:")
    print('  llama.cpp\\llama-server.exe -m models\\google_medgemma-4b-it-Q4_K_M.gguf --mmproj models\\mmproj-medgemma-4b-it-F16.gguf --port 8080 --ctx-size 4096 -ngl 0 --threads 6')


if __name__ == "__main__":
    main()