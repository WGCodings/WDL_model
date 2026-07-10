import json
from collections import Counter
from pathlib import Path

IN_FILE = Path("selfplay_data/positions.jsonl")
OUT_FILE = Path("selfplay_data/myWDL.json")

counter = Counter()

with open(IN_FILE) as f:
    for line in f:
        rec = json.loads(line)
        key = (rec["result"], rec["move"], rec["material"], rec["eval"])
        counter[key] += 1

out = {str(k): v for k, v in counter.items()}

with open(OUT_FILE, "w") as f:
    json.dump(out, f, indent=2)

print(f"Wrote {len(out)} unique (result, move, material, eval) tuples to {OUT_FILE}")