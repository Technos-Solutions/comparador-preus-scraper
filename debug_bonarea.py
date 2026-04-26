import requests
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Connectar Google Sheets
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
from oauth2client.service_account import ServiceAccountCredentials
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws = sheet.worksheet('Preus')

# Llegir primers 100 productes
print("📖 Llegint productes del Google Sheets...")
files = ws.get_all_records()
productes = files[:100]
print(f"✅ {len(productes)} productes llegits")

# Enviar a Groq per categoritzar
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

productes_text = "\n".join([
    f"{i}. {p['producte']} ({p['supermercat']})"
    for i, p in enumerate(productes)
])

prompt = f"""Categoritza aquests productes de supermercat en categories generals.

{productes_text}

Respon NOMÉS en JSON:
{{
  "categories": [
    {{
      "categoria": "Arròs i pasta",
      "ids": [0, 5, 12]
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
        'max_tokens': 2000
    }
)

resultat = response.json()
contingut = resultat['choices'][0]['message']['content']

try:
    dades = json.loads(contingut)
    print(f"\n=== {len(dades['categories'])} CATEGORIES DETECTADES ===")
    for cat in dades['categories']:
        print(f"\n📦 {cat['categoria']} ({len(cat['ids'])} productes)")
        for id_prod in cat['ids'][:3]:
            p = productes[id_prod]
            print(f"   [{p['supermercat']}] {p['producte']}")
        if len(cat['ids']) > 3:
            print(f"   ... i {len(cat['ids'])-3} més")
except Exception as e:
    print(f"Error: {e}")
    print(contingut)
