import pandas as pd
import csv
import re
import ast

INPUT = "saida.csv"
OUTPUT = "Dataframe_formatado.csv"

# ----------------- utils base -----------------
def to_str(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v)
    # normaliza NBSP e aspas
    s = s.replace("\xa0", " ").replace("\u2009", " ")
    s = s.replace("“", '"').replace("”", '"').replace("’", "'")
    s = s.strip()
    if s.lower() in {"", "none", "null", "nan"}:
        return None
    return s

def only_first_digits(text):
    s = to_str(text)
    if not s:
        return None
    m = re.search(r"\d+", s)
    return m.group(0) if m else None

def to_int_safe(text):
    d = only_first_digits(text)
    return int(d) if d is not None else None

def parse_decimal(text):
    s = to_str(text)
    if not s:
        return None
    m = re.search(r"(\d+[.,]?\d*)", s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None

# ----------------- peso / altura -----------------
def extrair_kg(peso):
    return parse_decimal(peso)

def altura_cm(tamanho):
    s = to_str(tamanho)
    if not s:
        return None
    # metros
    m = re.search(r"(\d+[.,]?\d*)\s*m\b", s, flags=re.I)
    if m:
        metros = float(m.group(1).replace(",", "."))
        return round(metros * 100, 2)
    # centímetros
    m = re.search(r"(\d+[.,]?\d*)\s*cm\b", s, flags=re.I)
    if m:
        return float(m.group(1).replace(",", "."))
    # fallback: número → assume cm
    val = parse_decimal(s)
    return val

# ----------------- efetividade -----------------
FRACTIONS_MAP = {"½": 0.5, "¼": 0.25, "¾": 0.75}

def _norm_mult(x):
    x = to_str(x)
    if not x:
        return None
    if x in FRACTIONS_MAP:
        return FRACTIONS_MAP[x]
    try:
        return float(x.replace(",", "."))
    except:
        return None

def extrair_efetividade(efetividade):
    s = to_str(efetividade)
    if not s:
        return {}
    try:
        d = ast.literal_eval(s)
        if isinstance(d, dict):
            return {k: _norm_mult(v) for k, v in d.items()}
    except Exception:
        pass
    return {}

# ----------------- habilidades -----------------
def extrair_habilidades(habilidades_str):
    s = to_str(habilidades_str)
    if not s:
        return pd.Series([None, None, None],
                         index=["habilidades_nomes", "habilidades_urls", "habilidades_descricoes"])
    try:
        habilidades = ast.literal_eval(s)  # lista de dicts
        if not isinstance(habilidades, list):
            return pd.Series([None, None, None],
                             index=["habilidades_nomes", "habilidades_urls", "habilidades_descricoes"])
        nomes, urls, descricoes = [], [], []
        for h in habilidades:
            if not isinstance(h, dict):
                continue
            nomes.append(to_str(h.get("nome")) or "None")
            urls.append(to_str(h.get("url")) or "None")
            descricoes.append(to_str(h.get("descricao")) or "None")
        return pd.Series(["; ".join(nomes), "; ".join(urls), "; ".join(descricoes)],
                         index=["habilidades_nomes", "habilidades_urls", "habilidades_descricoes"])
    except Exception:
        return pd.Series([None, None, None],
                         index=["habilidades_nomes", "habilidades_urls", "habilidades_descricoes"])

# ----------------- evoluções (respeitando ordem numero->dex, level->nível) -----------------
def _extract_dex_id(s, max_id=2000):
    """Extrai dex preferindo '#NNNN'. Evita confundir 'Level 26' com dex."""
    s = to_str(s)
    if not s:
        return None
    m = re.search(r"#\s*(\d{1,4})", s)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= max_id else None
    if "level" in s.lower():
        return None
    m2 = re.search(r"\b(\d{1,4})\b", s)
    if m2:
        n = int(m2.group(1))
        return n if 1 <= n <= max_id else None
    return None

def _extract_level(s, max_level=100):
    """Extrai nível; aceita 'Level 26' ou número ≤100; ignora strings com '#'."""
    s = to_str(s)
    if not s:
        return None
    m = re.search(r"[Ll]evel\D*(\d+)", s)
    if m:
        lv = int(m.group(1))
        return lv if 1 <= lv <= max_level else None
    if "#" in s or "http" in s.lower():
        return None
    m2 = re.search(r"\b(\d{1,3})\b", s)
    if m2:
        lv = int(m2.group(1))
        return lv if 1 <= lv <= max_level else None
    return None

def extrair_evolucoes_robusto(evol_str):
    """
    Respeita: numero = dex da próxima evolução, level = nível.
    Se vier invertido (ex.: numero='(Level 26)', level='#0051'), corrige.
    Retorna Series com strings separadas por ';' para:
    numero_evol, level_evol, item_evol, nome_evol, url_evol
    """
    idx = ['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol']
    s = to_str(evol_str)
    if not s:
        return pd.Series(['None'] * 5, index=idx)

    # 1) lista de objetos é o formato preferido
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, list):
            numeros, levels, items, nomes, urls = [], [], [], [], []
            for e in obj:
                if not isinstance(e, dict):
                    continue
                raw_num = e.get("numero")
                raw_lvl = e.get("level")

                dex = _extract_dex_id(raw_num) or _extract_dex_id(raw_lvl)
                lvl = _extract_level(raw_lvl) or _extract_level(raw_num)

                item = to_str(e.get("item")) or "None"
                nome = to_str(e.get("nome")) or "None"
                url  = to_str(e.get("url"))  or "None"

                if not any([dex, lvl, item != "None", nome != "None", url != "None"]):
                    continue

                numeros.append(str(dex) if dex is not None else "None")
                levels.append(str(lvl) if lvl is not None else "None")
                items.append(item)
                nomes.append(nome)
                urls.append(url)

            if numeros:
                return pd.Series([
                    "; ".join(numeros),
                    "; ".join(levels),
                    "; ".join(items),
                    "; ".join(nomes),
                    "; ".join(urls)
                ], index=idx)
    except Exception:
        pass

    # 2) fallback: string solta separada por ; / |
    def _split_multi(s2):
        if "|" in s2:
            return [x.strip() for x in s2.split("|") if x.strip()]
        if ";" in s2:
            return [x.strip() for x in s2.split(";") if x.strip()]
        return [s2.strip()]

    parts = _split_multi(s)
    numeros, levels, items, nomes, urls = [], [], [], [], []
    for p in parts:
        dex = _extract_dex_id(p)
        lvl = _extract_level(p)
        is_url = bool(re.search(r"https?://", p))
        maybe_item = ("stone" in p.lower() or "item" in p.lower())
        maybe_name = (not is_url) and (re.search(r"[A-Za-z]", p) is not None) and not maybe_item

        numeros.append(str(dex) if dex is not None else "None")
        levels.append(str(lvl) if lvl is not None else "None")
        items.append(p if maybe_item else "None")
        nomes.append(p if maybe_name else "None")
        urls.append(p if is_url else "None")

    if not numeros:
        return pd.Series(['None'] * 5, index=idx)

    return pd.Series([
        "; ".join(numeros),
        "; ".join(levels),
        "; ".join(items),
        "; ".join(nomes),
        "; ".join(urls)
    ], index=idx)

# ----------------- leitura / limpeza principal -----------------
df = pd.read_csv(
    INPUT,
    dtype=str,
    keep_default_na=False,
    na_values=[],
    quoting=csv.QUOTE_MINIMAL,
    quotechar='"',
    escapechar='\\',
    engine="python"
)

# normaliza numero para int (remove zeros à esquerda/#) antes de deduplicar
if "numero" in df.columns:
    df["numero"] = df["numero"].apply(to_int_safe)

# remove duplicatas por numero
if "numero" in df.columns:
    df = df.drop_duplicates(subset="numero", keep="first")

# Remover linhas totalmente nulas exceto campos ricos
cols_required = [c for c in df.columns if c not in {"proximas_evolucoes", "habilidades", "efetividade"}]
if cols_required:
    df.dropna(subset=cols_required, how="all", inplace=True)

# Peso/Altura
if "peso" in df.columns:
    df["Peso_kg"] = df["peso"].apply(extrair_kg)
if "tamanho" in df.columns:
    df["altura_cm"] = df["tamanho"].apply(altura_cm)

# Efetividade
if "efetividade" in df.columns:
    df["efetividade_dict"] = df["efetividade"].apply(extrair_efetividade)

# Evoluções -> 5 colunas (respeitando ordem numero/level, com correção)
if "proximas_evolucoes" in df.columns:
    df[['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol']] = \
        df['proximas_evolucoes'].apply(extrair_evolucoes_robusto)

# Habilidades -> 3 colunas
if "habilidades" in df.columns:
    df[['habilidades_nomes', 'habilidades_urls', 'habilidades_descricoes']] = \
        df['habilidades'].apply(extrair_habilidades)

# Tipos: normaliza espaços (mantém string "Tipo1, Tipo2")
def normalizar_tipos(s):
    s = to_str(s)
    if not s:
        return ""
    parts = [p.strip() for p in s.split(",")]
    return ", ".join([p for p in parts if p])

if "tipos" in df.columns:
    df["tipos"] = df["tipos"].apply(normalizar_tipos)

# Remover colunas cruas que não vamos exportar
for col in ['tamanho', 'peso', 'proximas_evolucoes', 'efetividade', 'habilidades']:
    if col in df.columns:
        df.drop(columns=[col], inplace=True)

# Ordena/garante colunas finais
final_cols = [
    "numero", "url", "nome", "tipos", "Peso_kg", "altura_cm",
    "efetividade_dict",
    "habilidades_nomes", "habilidades_urls", "habilidades_descricoes",
    "numero_evol", "level_evol", "item_evol", "nome_evol", "url_evol"
]
for c in final_cols:
    if c not in df.columns:
        df[c] = None
df = df[final_cols]

print(df.tail(5))

# Exporta sem índice e em UTF-8
df.to_csv(OUTPUT, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
print("OK! Gerado:", OUTPUT)
