from pymongo import MongoClient

mongo_url = "mongodb+srv://senac:senac@cluster0.pgo2wey.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_url)
db = client["Cluster0"]
coll = db["pokemons"]

# 1) Quantos Pokémons têm 2 tipos ou mais?
count_2oumais = coll.count_documents({ "tipos.1": { "$exists": True } })
print("Pokémons com 2 tipos ou mais:", count_2oumais)

# 2) Pokémons do tipo água cuja evolução ocorre depois do Level 30 (level numérico, plausível)
filtro = {
    "tipos": { 
        "$elemMatch": { "$regex": r"^water$|^água$", "$options": "i" }  # aceita "Water" ou "Água" (case-insensitive)
    },
    "evolucao.condicao.level": { "$type": "number", "$gt": 30, "$lte": 100 }
}
proj = { "_id": 0, "numero": 1, "nome": 1, "evolucao.condicao.level": 1 }

cursor = coll.find(filtro, proj).sort([("numero", 1)])
resultados = list(cursor)

print("\nPokémons de Água com evolução após level 30:")
for doc in resultados:
    lvl = (doc.get("evolucao") or {}).get("condicao", {}).get("level")
    print(f"#{doc.get('numero')} - {doc.get('nome')} (level {lvl})")

print("\nTotal encontrados:", len(resultados))
