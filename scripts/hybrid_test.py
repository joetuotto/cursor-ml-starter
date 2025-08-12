import os, json, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.hybrid.pipeline import run_batch, save_newswire
from src.hybrid.router import Item
import yaml

cfg = yaml.safe_load(open("config/hybrid.yaml","r",encoding="utf-8"))
items = [
    Item("1","Suomen Pankki nostaa ohjauskorkoa 25bp", "Korkopäätös vaikuttaa asuntolainoihin.", None, "fi", 0.9, 0.6, 0.7, "FI"),
    Item("2","Tech startup raises seed funding", "US startup closes $3M seed.", None, "en", 0.8, 0.2, 0.3, "US"),
    Item("3","ECB signals rate pause", "Macro update for euro area.", None, "en", 0.8, 0.6, 0.6, "EU"),
]

cards = run_batch(items, cfg)
print(json.dumps(cards, ensure_ascii=False, indent=2))
save_newswire(cards, cfg["output"]["newswire"])
print(f"Saved → {cfg['output']['newswire']}")
