import pandas as pd
import re
import ast

df = pd.read_csv("saida.csv")

def extrair_kg(peso):
  if pd.isna(peso):
    return None
  
  kilo = re.search(r"([\d\.]+)\s*kg", peso)
  if kilo:
    return float(kilo.group(1))
  return None

def altura_cm(tamanho):
    if pd.isna(tamanho):
        return None

    # Caso tenha metros (m)
    match_m = re.search(r"([\d,\.]+)\s*m", tamanho)
    if match_m:
        metros = float(match_m.group(1).replace(",", "."))
        return round(metros * 100, 2)

    # Caso tenha centímetros (cm) diretamente
    match_cm = re.search(r"([\d,\.]+)\s*cm", tamanho)
    if match_cm:
        return float(match_cm.group(1).replace(",", "."))

    return None

def extrair_evolucoes_robusto(evol_str):
    if pd.isna(evol_str) or str(evol_str).strip() == '':
        return pd.Series(['None']*5, index=['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol'])
    
    try:
        evol_str = str(evol_str).replace('""', '"').replace('\n', '')
        evol_list = ast.literal_eval(evol_str)

        numeros, levels, items, nomes, urls = [], [], [], [], []

        for evol in evol_list:
            # Ignora entradas que não têm nome ou número válido
            if evol.get('nome') is None and evol.get('numero') is None:
                continue
            numeros.append(str(evol.get('numero') or 'None'))
            levels.append(str(evol.get('level') or 'None'))
            items.append(str(evol.get('item') or 'None'))
            nomes.append(str(evol.get('nome') or 'None'))
            urls.append(str(evol.get('url') or 'None'))

        if not numeros:
            return pd.Series(['None']*5, index=['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol'])

        return pd.Series([
            "; ".join(numeros),
            "; ".join(levels),
            "; ".join(items),
            "; ".join(nomes),
            "; ".join(urls)
        ], index=['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol'])
    
    except Exception as e:
        print("Erro ao processar:", evol_str, e)
        return pd.Series(['None']*5, index=['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol'])
  
def extrair_habilidades(habilidades_str):
    try:
        # transforma a string "[{...}, {...}]" em lista de dicts
        habilidades = ast.literal_eval(habilidades_str)
        nomes = "; ".join(h['nome'] for h in habilidades)
        urls = "; ".join(h['url'] for h in habilidades)
        descricoes = "; ".join(h['descricao'] for h in habilidades)
        return pd.Series([nomes, urls, descricoes])
    except:
        return pd.Series([None, None, None])

def extrair_efetividade(efetividade):
    if pd.isna(efetividade) or efetividade.strip() == "":
        return {}
    try:
        return ast.literal_eval(efetividade)
    except Exception:
        return {}

# remove linhas duplicadas
df = df.drop_duplicates(subset="numero")
#Podemos usar subset="coluna" como parametro para tirar linhas duplicadas com base em alguma coluna
#Para complementar, podemos usar outro parametro, keep, sendo que tem keep= "first|last|False", sendo que o false
#remove todas as duplicatas (precisa usar o metodo de cima)

#Removendo linhas com valores nulos, usamos inplace true para alterar no df original (nao olhamos para a coluna de evolucao)
df.dropna(subset=[col for col in df.columns if col != 'proximas_evolucoes'], inplace=True)
#chamando funcao para extrair apenas os KG em uma nova coluna
df["Peso_kg"] = df["peso"].apply(extrair_kg)

#chamando funcao para converter metros para cm em uma nova coluna
df["altura_cm"] = df["tamanho"].apply(altura_cm)

# Cria uma coluna com o dicionário convertido
df["efetividade_dict"] = df["efetividade"].apply(extrair_efetividade)

# Expande o dicionário em várias colunas
efetividade_expandida = df["efetividade_dict"].apply(pd.Series)

#chamando funcao para pegar apenas o nome das evolucoes e colocando em uma nova coluna
df[['numero_evol', 'level_evol', 'item_evol', 'nome_evol', 'url_evol']] = df['proximas_evolucoes'].apply(extrair_evolucoes_robusto)

# Cria colunas novas só com os nomes das habilidades, url e desc de cada habilidade
df[['habilidades_nomes', 'habilidades_urls', 'habilidades_descricoes']] = df['habilidades'].apply(extrair_habilidades)

#Removendo colunas
df.drop(['tamanho', 'peso', 'proximas_evolucoes', 'efetividade', 'habilidades'], axis=1, inplace=True)

print(df.tail(5)) # mostra as 5 primeiras linhas

df.to_csv("Dataframe_formatado.csv")
