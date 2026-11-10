#!/usr/bin/env python3
"""Update v1/manifest.json after editing any data file.

Run from the repo root:  python3 scripts/build_manifest.py

- Writes a short sha256 per file under "hashes" (data files by key, meanings as "meanings/<code>").
  The app compares these hashes and downloads only the files that changed.
- Bumps "contentVersion" and "updatedAt" only when a hash changed (older app builds use contentVersion).
- Checks every file is valid JSON, so a broken file is never published.
"""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "v1" / "manifest.json"


def short_hash(path: pathlib.Path) -> str:
    data = path.read_bytes()
    json.loads(data)  # fail loudly on invalid JSON
    return hashlib.sha256(data).hexdigest()[:16]


def main() -> int:
    m = json.loads(MANIFEST.read_text())
    hashes = {}
    for key, rel in m["files"].items():
        hashes[key] = short_hash(ROOT / rel)
    for code, rel in m.get("meanings", {}).items():
        hashes[f"meanings/{code}"] = short_hash(ROOT / rel)

    if hashes == m.get("hashes"):
        print(f"No data changes. contentVersion stays {m['contentVersion']}.")
        return 0
    changed = sorted(k for k in hashes if hashes[k] != m.get("hashes", {}).get(k))
    m["hashes"] = hashes
    m["contentVersion"] = int(m["contentVersion"]) + 1
    m["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
    print(f"contentVersion -> {m['contentVersion']}. Changed: {', '.join(changed)}")
    print("After pushing, clear the jsDelivr cache so apps see it right away:")
    print("  curl https://purge.jsdelivr.net/gh/nazmul-hussain/oxvox-cdn@main/v1/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
