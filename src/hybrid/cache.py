import os, json, time, hashlib
from pathlib import Path

def _key(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)

def get_cache(cache_dir: str, key: str, ttl_hours: int):
    f = Path(cache_dir) / f"{key}.json"
    if not f.exists():
        return None
    age_h = (time.time() - f.stat().st_mtime) / 3600.0
    if age_h > ttl_hours:
        return None
    try:
        return json.loads(f.read_text())
    except:
        return None

def set_cache(cache_dir: str, key: str, data):
    ensure_dir(cache_dir)
    f = Path(cache_dir) / f"{key}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def make_item_key(item, prompt_version: str) -> str:
    ident = f"{item.url}|{item.title}|{item.lang}|{prompt_version}"
    return _key(ident)
