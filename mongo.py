import re
import ast
import pandas as pd
from pymongo import MongoClient, UpdateOne

CSV_PATH = "Dataframe_formatado.csv"

mongo_url = "mongodb+srv://senac:senac@cluster0.pgo2wey.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_url)

db = client["Cluster0"]
coll = db["pokemons"]

coll.drop()
print("Coleção 'pokemons' apagada com sucesso!")

INT64_MAX = 9223372036854775807

def to_null(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in {"none", "null", "nan", ""}:
        return None
    return s

def to_int(v):
    v = to_null(v)
    if v is None:
        return None
    m = re.search(r"\d+", str(v))
    if not m:
        return None
    val = int(m.group(0))
    if val > INT64_MAX:
        return None
    return val

def to_level(v, max_level=100):
    s = to_null(v)
    if s is None:
        return None
    m = re.search(r"[Ll]evel\D*(\d+)", s)
    if m:
        lv = int(m.group(1))
        return lv if 1 <= lv <= max_level else None
    if "#" in s or "http" in s.lower():
        return None
    m2 = re.search(r"\d+", s)
    if not m2:
        return None
    lv = int(m2.group(0))
    return lv if 1 <= lv <= max_level else None

def to_float(v):
    v = to_null(v)
    if v is None:
        return None
    s = str(v).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def parse_tipos(v):
    v = to_null(v)
    if not v:
        return []
    return [x.strip() for x in str(v).split(",") if x.strip()]

FRACTIONS_MAP = {"½": 0.5, "¼": 0.25, "¾": 0.75}

def normalize_multiplier(s):
    if s in FRACTIONS_MAP:
        return FRACTIONS_MAP[s]
    try:
        return float(str(s).replace(",", "."))
    except Exception:
        return None

def parse_efetividade_dict(v):
    v = to_null(v)
    if not v:
        return {}
    try:
        d = ast.literal_eval(v)
        if isinstance(d, dict):
            return {k: normalize_multiplier(val) for k, val in d.items()}
        return {}
    except Exception:
        return {}

def split_multi(v):
    v = to_null(v)
    if not v:
        return []
    txt = str(v)
    if "|" in txt:
        return [x.strip() for x in txt.split("|") if x.strip()]
    if ";" in txt:
        return [x.strip() for x in txt.split(";") if x.strip()]
    return [txt.strip()]

def build_habilidades(row):
    nomes = split_multi(row.get("habilidades_nomes"))
    urls  = split_multi(row.get("habilidades_urls"))
    descs = split_multi(row.get("habilidades_descricoes"))
    n = max(len(nomes), len(urls), len(descs))
    out = []
    for i in range(n):
        h = {
            "nome": nomes[i] if i < len(nomes) else None,
            "url":  urls[i]  if i < len(urls)  else None,
            "descricao": descs[i] if i < len(descs) else None,
        }
        if any(to_null(v) is not None for v in h.values()):
            out.append(h)
    return out

def build_evolucao(row):
    num_raw = split_multi(row.get("numero_evol"))
    lvl_raw = split_multi(row.get("level_evol"))
    item_raw = split_multi(row.get("item_evol"))
    nome_raw = split_multi(row.get("nome_evol"))
    url_raw  = split_multi(row.get("url_evol"))

    num = next((to_int(x) for x in num_raw if to_int(x) is not None), None)
    lvl = next((to_level(x) for x in lvl_raw if to_level(x) is not None), None)
    item = next((to_null(x) for x in item_raw if to_null(x) is not None and to_null(x).lower() != "none"), None)
    nome = next((to_null(x) for x in nome_raw if to_null(x) is not None and to_null(x).lower() != "none"), None)
    url  = next((to_null(x) for x in url_raw  if to_null(x) is not None and to_null(x).lower()  != "none"), None)

    if all(x is None for x in [num, lvl, item, nome, url]):
        return None

    evo = {}
    if num is not None:  evo["numero"] = num
    if nome is not None: evo["nome"]   = nome
    if url is not None:  evo["url"]    = url
    cond = {}
    if lvl is not None:  cond["level"] = lvl
    if item is not None: cond["item"]  = item
    if cond:
        evo["condicao"] = cond
    return evo

def validate_doc(d):
    def _chk(x):
        if isinstance(x, int) and (x < -INT64_MAX-1 or x > INT64_MAX):
            return False
        return True

    for k in ("numero",):
        if k in d and d[k] is not None and not _chk(d[k]):
            print(f"[WARN] int64 overflow em '{k}':", d[k], "=> descartando campo")
            d[k] = None

    evo = d.get("evolucao")
    if isinstance(evo, dict):
        if "numero" in evo and evo["numero"] is not None and not _chk(evo["numero"]):
            print(f"[WARN] int64 overflow em 'evolucao.numero':", evo["numero"], "=> removendo numero da evolução")
            evo["numero"] = None
        cond = evo.get("condicao")
        if isinstance(cond, dict) and "level" in cond and cond["level"] is not None and not _chk(cond["level"]):
            print(f"[WARN] int64 overflow em 'evolucao.condicao.level':", cond["level"], "=> removendo level da evolução")
            cond["level"] = None

    return True

df = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False, na_values=[])

cols_to_drop = [c for c in df.columns if c.startswith("Unnamed") or c.strip() == ""]
if cols_to_drop:
    df.drop(columns=cols_to_drop, inplace=True)

docs = []
for idx, row in df.iterrows():
    doc = {
        "numero": to_int(row.get("numero")),
        "url": to_null(row.get("url")),
        "nome": to_null(row.get("nome")),
        "tipos": parse_tipos(row.get("tipos")),
        "peso_kg": to_float(row.get("Peso_kg")),
        "altura_cm": to_float(row.get("altura_cm")),
        "efetividade": parse_efetividade_dict(row.get("efetividade_dict")),
        "habilidades": build_habilidades(row),
        "evolucao": build_evolucao(row),
    }

    validate_doc(doc)
    doc = {k: v for k, v in doc.items() if v is not None}
    docs.append(doc)

ops = []
for d in docs:
    if d.get("numero") is not None:
        ops.append(UpdateOne({"numero": d["numero"]}, {"$set": d}, upsert=True))
    else:
        ops.append(UpdateOne({"nome": d.get("nome")}, {"$set": d}, upsert=True))

if ops:
    result = coll.bulk_write(ops, ordered=False)
    print("Upserts:", result.upserted_count, "Modified:", result.modified_count)
else:
    print("Nenhum documento para inserir.")
