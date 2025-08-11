# scripts/validate_trends.py
import json, sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.validation.schema import validate_card

def main():
    paths = [Path("artifacts/feeds/trends.en.json"), Path("artifacts/feeds/trends.fi.json")]
    failed = 0
    for p in paths:
        if not p.exists():
            print(f"[WARN] missing {p}")
            continue
        data = json.loads(p.read_text())
        for i,card in enumerate(data):
            errs = validate_card(card)
            if errs:
                failed += 1
                print(f"[FAIL] {p} item#{i}: {' | '.join(errs)}")
    if failed:
        print(f"❌ Validation failed on {failed} items")
        sys.exit(1)
    print("✅ Validation passed")
if __name__ == "__main__":
    main()
