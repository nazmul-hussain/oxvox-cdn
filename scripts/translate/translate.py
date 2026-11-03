#!/usr/bin/env python3
"""Generate and verify word meanings for every app language, fully offline.

Model: Meta NLLB-200 (distilled 600M), run locally with PyTorch. No API keys, no network
calls after the first model download.

Source:  v1/data/words.json (English word, example, Bangla meaning).
Output:  v1/data/meanings/<code>.json, plus manifest.meanings and contentVersion.

Per language, for every word:
  1. Translate the English word into the language (en -> target), and the Bangla
     meaning into the language (bn -> target). Bangla gives the intended sense.
  2. Pick the first candidate that passes the rule checks (script, not empty, not the
     English word, no repeated-token junk, short).
  3. Back-translate the candidate to English and require it to match the English word.
     Failed words are retried one at a time with more beam candidates.
  4. Words that still fail are rejected and left out (the app falls back to Bangla).

Usage (from the oxvox-cdn repo root, inside the venv created for this script):
  scripts/translate/.venv/bin/python scripts/translate/translate.py run --limit 50 --lang hi
  scripts/translate/.venv/bin/python scripts/translate/translate.py run
  scripts/translate/.venv/bin/python scripts/translate/translate.py report
  scripts/translate/.venv/bin/python scripts/translate/translate.py publish

State is kept in scripts/translate/work/ (git-ignored), so interrupted runs resume.
"""

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS = ROOT / "v1/data/words.json"
MANIFEST = ROOT / "v1/manifest.json"
OUT_DIR = ROOT / "v1/data/meanings"
WORK = Path(__file__).resolve().parent / "work"

MODEL_NAME = "facebook/nllb-200-distilled-600M"
BATCH = 16  # smaller batches keep activation memory low
SRC_EN = "eng_Latn"
SRC_BN = "ben_Beng"

# app code: (English name, NLLB code, script regex a valid gloss must match, None = Latin)
LANGS = {
    "hi": ("Hindi", "hin_Deva", r"[\u0900-\u097F]"),
    "ur": ("Urdu", "urd_Arab", r"[\u0600-\u06FF]"),
    "fa": ("Persian", "pes_Arab", r"[\u0600-\u06FF]"),
    "he": ("Hebrew", "heb_Hebr", r"[\u0590-\u05FF]"),
    "ne": ("Nepali", "npi_Deva", r"[\u0900-\u097F]"),
    "si": ("Sinhala", "sin_Sinh", r"[\u0D80-\u0DFF]"),
    "ta": ("Tamil", "tam_Taml", r"[\u0B80-\u0BFF]"),
    "te": ("Telugu", "tel_Telu", r"[\u0C00-\u0C7F]"),
    "zh": ("Chinese", "zho_Hans", r"[\u4E00-\u9FFF]"),
    "ja": ("Japanese", "jpn_Jpan", r"[\u3040-\u30FF\u4E00-\u9FFF]"),
    "ko": ("Korean", "kor_Hang", r"[\uAC00-\uD7AF]"),
    "th": ("Thai", "tha_Thai", r"[\u0E00-\u0E7F]"),
    "vi": ("Vietnamese", "vie_Latn", None),
    "id": ("Indonesian", "ind_Latn", None),
    "ms": ("Malay", "zsm_Latn", None),
    "fil": ("Filipino", "tgl_Latn", None),
    "es": ("Spanish", "spa_Latn", None),
    "pt": ("Portuguese", "por_Latn", None),
    "fr": ("French", "fra_Latn", None),
    "de": ("German", "deu_Latn", None),
    "it": ("Italian", "ita_Latn", None),
    "ru": ("Russian", "rus_Cyrl", r"[\u0400-\u04FF]"),
    "uk": ("Ukrainian", "ukr_Cyrl", r"[\u0400-\u04FF]"),
    "pl": ("Polish", "pol_Latn", None),
    "tr": ("Turkish", "tur_Latn", None),
    "sw": ("Swahili", "swh_Latn", None),
    "am": ("Amharic", "amh_Ethi", r"[\u1200-\u137F]"),
    "ha": ("Hausa", "hau_Latn", None),
}


# ---------- model ----------

_model = None
_tok = None
_device = None


MEM_LIMIT_GB = 4.5  # safety stop; PyTorch itself needs about 3 GB here


def _watchdog() -> None:
    """macOS ignores ulimit for memory, so check our own RSS and stop if it goes over the cap."""
    import os
    import threading

    import psutil

    proc = psutil.Process()

    def loop():
        while True:
            time.sleep(2)
            rss_gb = proc.memory_info().rss / 1024**3
            if rss_gb > MEM_LIMIT_GB:
                print(f"memory {rss_gb:.2f} GB over {MEM_LIMIT_GB} GB cap, exiting", flush=True)
                os._exit(3)

    threading.Thread(target=loop, daemon=True).start()


def load_model():
    global _model, _tok, _device
    if _model is not None:
        return
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _device = "mps" if torch.backends.mps.is_available() else "cpu"
    # float16 on the GPU halves the weight memory (~1.2 GB instead of ~2.4 GB).
    dtype = torch.float16 if _device == "mps" else torch.float32
    _tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, torch_dtype=dtype).to(_device).eval()
    _watchdog()


def translate(texts: list[str], src: str, tgt: str, beams: int = 4, returns: int = 1) -> list[list[str]]:
    """Returns, for each input, `returns` candidate translations (best first)."""
    import torch

    load_model()
    _tok.src_lang = src
    enc = _tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=64).to(_device)
    with torch.no_grad():
        out = _model.generate(
            **enc,
            forced_bos_token_id=_tok.convert_tokens_to_ids(tgt),
            max_new_tokens=24,
            num_beams=max(beams, returns),
            num_return_sequences=returns,
        )
    decoded = _tok.batch_decode(out, skip_special_tokens=True)
    return [decoded[i * returns : (i + 1) * returns] for i in range(len(texts))]


def translate_many(texts: list[str], src: str, tgt: str, beams: int = 4) -> list[str]:
    results: list[str] = []
    for i in range(0, len(texts), BATCH):
        results += [c[0] for c in translate(texts[i : i + BATCH], src, tgt, beams)]
    return results


# ---------- data ----------

def load_words(limit: int | None) -> list[dict]:
    words = json.loads(WORDS.read_text(encoding="utf-8"))
    rows = [
        {
            "id": w.get("id") or w["word"].lower(),
            "word": w["word"],
            "bn": w.get("meaning", "").strip(),
        }
        for w in words
    ]
    return rows[:limit] if limit else rows


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


# ---------- rule checks ----------

def rule_ok(lang: str, word: str, value: str) -> str | None:
    """Returns the problem, or None when the candidate passes."""
    script = LANGS[lang][2]
    if not value or not value.strip():
        return "empty"
    if len(value) > 60 or "\n" in value:
        return "too long"
    if value.lower().strip(" .") == word.lower():
        return "same as English word"
    tokens = value.split()
    if len(tokens) > 1 and len(set(tokens)) == 1:
        return "repeated token"
    if script and not re.search(script, value):
        return "wrong script"
    if script is None and any(
        unicodedata.category(c).startswith("L") and ord(c) > 0x024F for c in value
    ):
        return "non-Latin letters"
    return None


# ---------- back-translation check ----------

def _stem(word: str) -> str:
    return word.lower()[: max(4, len(word) - 2)]


def back_matches(word: str, back: str) -> bool:
    """True when the English back-translation carries the original word (or its stem)."""
    w = word.lower()
    b = re.sub(r"[^a-z\s'-]", " ", back.lower())
    if w in b.split() or w in b:
        return True
    stem = _stem(word)
    return any(t.startswith(stem) for t in b.split())


# ---------- per-language pipeline ----------

def run_language(lang: str, rows: list[dict], shard: str) -> str:
    WORK.mkdir(parents=True, exist_ok=True)
    name, nllb, _ = LANGS[lang]
    state_path = WORK / f"{lang}.{shard}.state.json"
    state = load_json(state_path, {"cand_en": {}, "cand_bn": {}, "final": {}, "rejected": {}})
    todo = [r for r in rows if r["id"] not in state["final"] and r["id"] not in state["rejected"]]
    print(f"[{lang}] {len(todo)} words to process ({name})", flush=True)

    def pass_check(items: list[tuple[dict, str]]) -> dict[str, str]:
        """items: (row, candidate). Returns id -> candidate that passes rules and back-translates."""
        items = [(r, c) for r, c in items if c and rule_ok(lang, r["word"], c) is None]
        if not items:
            return {}
        backs = translate_many([c for _, c in items], nllb, SRC_EN, beams=4)
        return {r["id"]: c for (r, c), b in zip(items, backs) if back_matches(r["word"], b)}

    # 1. English -> target candidates; keep the ones that pass the checks.
    need_en = [r for r in todo if r["id"] not in state["cand_en"]]
    if need_en:
        outs = translate_many([r["word"] for r in need_en], SRC_EN, nllb, beams=5)
        state["cand_en"].update({r["id"]: c for r, c in zip(need_en, outs)})
    ok_en = pass_check([(r, state["cand_en"][r["id"]]) for r in todo])
    state["final"].update(ok_en)

    # 2. Words without a verified English candidate: try the Bangla meaning as the source.
    rest = [r for r in todo if r["id"] not in state["final"] and r["bn"]]
    need_bn = [r for r in rest if r["id"] not in state["cand_bn"]]
    if need_bn:
        outs = translate_many([r["bn"] for r in need_bn], SRC_BN, nllb, beams=5)
        state["cand_bn"].update({r["id"]: c for r, c in zip(need_bn, outs)})
    ok_bn = pass_check([(r, state["cand_bn"][r["id"]]) for r in rest])
    state["final"].update(ok_bn)

    # 3. Still failing: one word at a time with more beam candidates (batching hurts some scripts).
    for r in todo:
        if r["id"] in state["final"]:
            continue
        options = translate([r["word"]], SRC_EN, nllb, beams=8, returns=5)[0]
        if r["bn"]:
            options += translate([r["bn"]], SRC_BN, nllb, beams=8, returns=5)[0]
        picked = None
        for cand in options:
            if rule_ok(lang, r["word"], cand) is None:
                back = translate([cand], nllb, SRC_EN, beams=4)[0][0]
                if back_matches(r["word"], back):
                    picked = cand
                    break
        if picked:
            state["final"][r["id"]] = picked
        else:
            state["rejected"][r["id"]] = "no candidate back-translated to the word"
    save_json(state_path, state)

    return f"[{lang} {shard}] {len(state['final'])} ok, {len(state['rejected'])} rejected of {len(rows)}"


# ---------- merge shards ----------

def merge() -> None:
    """Combine every shard's state into work/<lang>.final.json and .rejected.json."""
    for lang in LANGS:
        final, rejected = {}, {}
        for f in sorted(WORK.glob(f"{lang}.s*of*.state.json")):
            st = json.loads(f.read_text(encoding="utf-8"))
            final.update(st["final"])
            rejected.update(st["rejected"])
        if final or rejected:
            save_json(WORK / f"{lang}.final.json", dict(sorted(final.items())))
            save_json(WORK / f"{lang}.rejected.json", rejected)
            print(f"merged {lang}: {len(final)} ok, {len(rejected)} rejected")


# ---------- publish and report ----------

def publish() -> None:
    merge()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    meanings = manifest.get("meanings", {})
    published = 0
    for lang in LANGS:
        f = WORK / f"{lang}.final.json"
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        if not data:
            continue
        rel = f"v1/data/meanings/{lang}.json"
        save_json(ROOT / rel, data)
        meanings[lang] = rel
        published += 1
        print(f"published {lang}: {len(data)} words")
    if not published:
        sys.exit("Nothing to publish. Run `run` first.")
    manifest["meanings"] = dict(sorted(meanings.items()))
    manifest["contentVersion"] = int(manifest.get("contentVersion", 0)) + 1
    manifest["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_json(MANIFEST, manifest)
    print(f"manifest contentVersion -> {manifest['contentVersion']}")


def report(total: int) -> None:
    merge()
    for lang, (name, _, _) in LANGS.items():
        f = WORK / f"{lang}.final.json"
        if not f.exists():
            print(f"{lang:4} {name:12} not run")
            continue
        n = len(json.loads(f.read_text(encoding="utf-8")))
        print(f"{lang:4} {name:12} {n}/{total} ({100 * n // total}%)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["run", "publish", "report", "merge"])
    ap.add_argument("--shard", default="1/1", help="k/N: this process handles every Nth word")
    ap.add_argument("--lang", help="comma-separated app codes, default all")
    ap.add_argument("--limit", type=int, help="only the first N words (trial)")
    args = ap.parse_args()

    if args.command == "publish":
        return publish()
    if args.command == "merge":
        return merge()
    rows = load_words(args.limit)
    k, n = (int(x) for x in args.shard.split("/"))
    rows = [r for i, r in enumerate(rows) if i % n == k - 1]
    shard = f"s{k}of{n}"
    if args.command == "report":
        return report(len(rows))

    langs = args.lang.split(",") if args.lang else list(LANGS)
    unknown = [l for l in langs if l not in LANGS]
    if unknown:
        sys.exit(f"Unknown language codes: {unknown}")
    for lang in langs:
        print(run_language(lang, rows, shard), flush=True)


if __name__ == "__main__":
    main()
