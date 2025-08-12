import os, json, time, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def read_usage(path=".cache/hybrid/usage.json"):
    if not os.path.exists(path): return {"deepseek_eur":0.0,"gpt5_eur":0.0}
    try: return json.load(open(path,"r"))
    except: return {"deepseek_eur":0.0,"gpt5_eur":0.0}

def write_usage(u, path=".cache/hybrid/usage.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(u, open(path,"w"), indent=2)

def add_cost(model, eur, path=".cache/hybrid/usage.json"):
    u = read_usage(path)
    key = "deepseek_eur" if model == "deepseek" else "gpt5_eur"
    u[key] = float(u.get(key,0.0)) + float(eur)
    write_usage(u, path)

if __name__ == "__main__":
    u = read_usage()
    ds = u.get("deepseek_eur",0.0); g5 = u.get("gpt5_eur",0.0)
    print(json.dumps({"deepseek_month_eur":ds,"gpt5_month_eur":g5,"total":ds+g5}, indent=2))
