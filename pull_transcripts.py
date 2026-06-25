#!/usr/bin/env python3
"""
pull_transcripts.py
Fetch YouTube transcripts via Supadata and save one Markdown file per video
into research/youtube-transcripts/.

Setup:
  pip install requests
  export SUPADATA_API_KEY="your_key_here"   # never hardcode; keep it out of git

Run from your repo root:
  python pull_transcripts.py
"""

import os
import sys
import time
import datetime
import pathlib
import requests

API_KEY = os.environ.get("SUPADATA_API_KEY")
if not API_KEY:
    sys.exit("Missing SUPADATA_API_KEY. Run: export SUPADATA_API_KEY='your_key'")

OUT_DIR = pathlib.Path("research/youtube-transcripts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://api.supadata.ai/v1/transcript"
HEADERS = {"x-api-key": API_KEY}

# ---- Edit this list. (slug, expert name, video url) ----
# slug becomes the filename, so keep it short, lowercase, hyphenated.
VIDEOS = [
    ("kyle-cj-newsletter-growth", "Kyle Poyar & CJ Gustafson", "https://www.youtube.com/watch?v=RX68Jm556Ao"),
    ("mcgarry-1k-subscribers-qa", "Matt McGarry", "https://www.youtube.com/watch?v=aAmm5Bm_odI"),
    ("mcgarry-growth-tier-list", "Matt McGarry", "https://www.youtube.com/watch?v=ZllqhESam1k"),
    ("geisler-behavior-based-lifecycle", "Val Geisler", "https://www.youtube.com/watch?v=C4DKWaoGENw"),
    ("schwedelson-inbound-2025", "Jay Schwedelson", "https://www.youtube.com/watch?v=zKrjlaSiIDg"),
    ("bourgoin-buyer-psychology", "Katelyn Bourgoin", "https://www.youtube.com/watch?v=V4SHt99AXqM"), 
]


def fetch(url):
    # mode=native => only existing captions (no AI-generation credit cost)
    r = requests.get(
        BASE,
        headers=HEADERS,
        params={"url": url, "text": "true", "mode": "native"},
        timeout=60,
    )
    if r.status_code == 200:
        return r.json()
    if r.status_code == 202:  # async job for long videos
        job = r.json()
        job_id = job.get("jobId") or job.get("id")
        for _ in range(30):
            time.sleep(3)
            p = requests.get(f"{BASE}/{job_id}", headers=HEADERS, timeout=60).json()
            status = p.get("status")
            if status in ("completed", "succeeded", None) and p.get("content"):
                return p
            if status == "failed":
                raise RuntimeError(f"job failed: {url}")
        raise TimeoutError(f"job timed out: {url}")
    raise RuntimeError(f"{r.status_code}: {r.text[:200]}")


def main():
    saved = skipped = errors = 0
    for slug, expert, url in VIDEOS:
        path = OUT_DIR / f"{slug}.md"
        if path.exists():
            print(f"skip (exists): {path.name}")
            skipped += 1
            continue
        try:
            data = fetch(url)
        except Exception as e:
            print(f"ERROR {slug}: {e}")
            errors += 1
            continue
        content = data.get("content", "")
        lang = data.get("lang", "")
        today = datetime.date.today().isoformat()
        header = (
            f"# {expert} - transcript\n\n"
            f"- Source: {url}\n"
            f"- Language: {lang}\n"
            f"- Pulled: {today}\n"
            f"- MY TAKE: _add one honest line after you read/skim this_\n\n"
            f"---\n\n"
        )
        path.write_text(header + content, encoding="utf-8")
        print(f"saved: {path.name} ({len(content)} chars)")
        saved += 1

    print(f"\nDone. saved={saved} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    main()
