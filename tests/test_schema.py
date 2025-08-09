import json
import pathlib

from jsonschema import Draft202012Validator


def test_feed_item_schema_loads_and_validates_minimal() -> None:
    schema_path = pathlib.Path("artifacts/feed_item_schema.json")
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
    sample = {
        "id": "sig-demo-1",
        "title": "Demo title",
        "lede": "Short lede sentence.",
        "category": "economy",
        "sources": ["https://example.com/a"],
        "symbolic_art": {
            "style": "symbolist-minimal",
            "palette": ["#0A2342", "#FF7A00", "#F2F4F7", "#1A1F2B"],
            "category": "economy",
            "alt": "Symbolic chart",
            "svg": (
                "<svg viewBox='0 0 320 180' xmlns='http://www.w3.org/2000/svg'>"
                "<rect width='320' height='180' fill='#0A2342'/></svg>"
            ),
        },
        "cta": {"label": "Download report", "url": "/api/download?id=report"},
        "published_at": "2025-01-01T00:00:00Z",
    }
    Draft202012Validator(schema).validate(sample)
