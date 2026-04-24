import requests
import json
import os

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Productes d'exemple d'arròs de diferents supermercats
productes = [
    {"id": 0, "supermercat": "Mercadona", "producte": "Arroz redondo Hacendado", "quantitat": "1 kg", "preu": 1.30},
    {"id": 1, "supermercat": "Mercadona", "producte": "Arroz largo Hacendado", "quantitat": "1 kg", "preu": 1.25},
    {"id": 2, "supermercat": "Dia", "producte": "Arroz redondo Dia", "quantitat": "1 kg", "preu": 1.19},
    {"id": 3, "supermercat": "Carrefour", "producte": "Arroz redondo Carrefour", "quantitat": "1 kg", "preu": 1.15},
    {"id": 4, "supermercat": "Bon Àrea", "producte": "Arros rodó", "quantitat": "1 kg", "preu": 1.22},
    {"id": 5, "supermercat": "Bon Preu / Esclat", "producte": "Arròs rodó", "quantitat": "1 kg", "preu": 1.18},
    {"id": 6, "supermercat": "Mercadona", "producte": "Arroz largo Hacendado", "quantitat": "500 g", "preu": 0.75},
    {"id": 7, "supermercat": "Dia", "producte": "Arroz largo Dia", "quantitat": "1 kg", "preu": 1.15},
]

productes_text = "\n".join([
    f"{p['id']}. [{p['supermercat']}] {p['producte']} {p['quantitat']} — {p['preu']}€"
    for p in productes
])

prompt = f"""Tens aquesta llista de productes de diferents supermercats:

{productes_text}

Agrupa els productes que són el MATEIX article (mateix tipus i mateixa quantitat aproximada).
No agruppis productes de mides diferents (1kg vs 500g són grups separats).

Respon NOMÉS en JSON sense cap text addicional:
{{
  "grups": [
    {{
      "nom_normalitzat": "Arròs rodó 1kg",
      "ids": [0, 2, 3, 4, 5]
    }}
  ]
}}"""

response = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        'model': 'llama-3.3-70b-versatile',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.1,
        'max_tokens': 1000
    }
)

resultat = response.json()
contingut = resultat['choices'][0]['message']['content']
print("=== RESPOSTA GROQ ===")
print(contingut)

# Parsejar i mostrar resultat
try:
    dades = json.loads(contingut)
    print("\n=== GRUPS DETECTATS ===")
    for grup in dades['grups']:
        print(f"\n📦 {grup['nom_normalitzat']}")
        for id_prod in grup['ids']:
            p = productes[id_prod]
            print(f"   [{p['supermercat']}] {p['producte']} {p['quantitat']} — {p['preu']}€")
except:
    print("Error parsejant JSON")
