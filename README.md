# 📊 Pipeline Pokémon com Scrapy, Pandas e MongoDB

Projeto desenvolvido para **extração, transformação e análise de dados da Pokédex** a partir do site [Pokémon Database](https://pokemondb.net/pokedex/all).

O objetivo é demonstrar um **pipeline completo de ETL** (Extract, Transform, Load) utilizando:
- **Scrapy** → coleta estruturada dos dados.
- **Pandas** → limpeza, normalização e transformação.
- **MongoDB** → armazenamento em documentos e consultas analíticas.

---

## 🚀 Funcionalidades
- Coleta automatizada da Pokédex:
  - Número e nome do Pokémon.
  - URL da página.
  - Altura (cm) e peso (kg).
  - Tipos (água, fogo, veneno...).
  - Habilidades (nome, URL, descrição).
  - Efetividade contra outros tipos.
  - Cadeia de evolução (nível/item/condição).
- Normalização com Pandas:
  - Conversão de alturas, pesos e frações.
  - Padronização de colunas de evolução e habilidades.
- Armazenamento no MongoDB:
  - Modelo documental flexível.
  - `upsert` para evitar duplicação.
- Consultas de exemplo:
  - Quantos Pokémon possuem 2 ou mais tipos.
  - Pokémon de Água cuja evolução ocorre após o **Level 30**.

---

## 📂 Estrutura do repositório
```
.
├── scrapy_spider/        # Código do Scrapy para coleta
├── pandas_cleaning/      # Scripts de limpeza e normalização
├── mongo_scripts/        # Código para inserção/consultas no MongoDB
├── slides/               # Apresentação em LaTeX Beamer
└── README.md             # Este arquivo
```

---

## ⚙️ Requisitos
- Python 3.9+
- MongoDB rodando local ou em cluster (Atlas, Docker, etc.)
- Bibliotecas Python:
  ```bash
  pip install scrapy pandas pymongo
  ```

---

## ▶️ Como executar

### 1. Scraping
Rode o spider do Scrapy para gerar os dados:
```bash
scrapy runspider main.py -o saida.csv
```

### 2. Limpeza/Transformação
Execute o script de normalização com Pandas:
```bash
python limpeza_dados.py saida.csv Dataframe_formatado.csv
```

### 3. Inserção no MongoDB
Carregue os dados tratados:
```bash
python Dataframe_formatado.csv Dataframe_formatado.csv
```

### 4. Consultas
Exemplo: Pokémon com 2 tipos ou mais e evoluções de Água acima do level 30.
```bash
python consultas.py
```

---

## 🗂️ Modelo do documento no MongoDB
```json
{
  "numero": 7,
  "nome": "Squirtle",
  "tipos": ["Water"],
  "peso_kg": 9.0,
  "altura_cm": 50.0,
  "efetividade": {"Electric": 2.0, "Fire": 0.5},
  "habilidades": [
    {"nome": "Torrent", "url": "...", "descricao": "..."}
  ],
  "evolucao": {
    "numero": 8,
    "nome": "Wartortle",
    "condicao": {"level": 16}
  }
}
```

---

## 🖼️ Arquitetura da solução
Fluxo de dados do pipeline:

```
Scrapy → Pandas → MongoDB → Consultas
```

- **Scrapy** coleta da Pokédex.  
- **Pandas** limpa, normaliza e transforma.  
- **MongoDB** armazena com `upsert`.  
- **Consultas** respondem perguntas analíticas.

---

## 📊 Resultados de exemplo

- **Pokémon com 2 tipos ou mais:** `526`  
- **Pokémon de Água com evolução após level 30:**
  ```
  #7   - Squirtle (level 36)
  #79  - Slowpoke (level 37)
  #258 - Mudkip (level 36)
  #363 - Spheal (level 44)
  #393 - Piplup (level 36)
  #501 - Oshawott (level 36)
  #502 - Dewott (level 36)
  #535 - Tympole (level 36)
  #656 - Froakie (level 36)
  #728 - Popplio (level 34)
  #816 - Sobble (level 35)
  #912 - Quaxly (level 36)

  Total encontrados: 12
  ```

---

## 👥 Autores
- Pedro Gomes  
- Edinaldo Júnior  
- André Luís  

---


