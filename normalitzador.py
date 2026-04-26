import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import requests
import time
from datetime import datetime

print("="*60)
print(f"🚀 NORMALITZADOR INICIAT - {datetime.now()}")
print("="*60)

# Connectar Google Sheets
try:
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open('Comparador_Preus_DB')
    print("✅ Connectat a Google Sheets")
except Exception as e:
    print(f"❌ Error connectant: {e}")
    exit(1)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

def cridar_groq(prompt, max_intents=3):
    """Crida a Groq amb reintents"""
    for intent in range(max_intents):
        try:
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
                },
                timeout=30
            )
            resultat = response.json()
            if 'choices' not in resultat:
                print(f"  ⚠️ Resposta inesperada: {resultat}")
                time.sleep(10)
                continue
            contingut = resultat['choices'][0]['message']['content']
            contingut_net = contingut.replace('```json', '').replace('```', '').strip()
            return json.loads(contingut_net)
        except Exception as e:
            print(f"  ⚠️ Error intent {intent+1}: {e}")
            time.sleep(15)
    return None

def categoritzar_lot(productes):
    """Categoritza un lot de productes amb Groq"""
    productes_text = "\n".join([
        f"{i}. {p['producte']} ({p['supermercat']}) {p['quantitat']}"
        for i, p in enumerate(productes)
    ])

    prompt = f"""Categoritza aquests productes de supermercat en categories generals en català.

{productes_text}

Utilitza categories com: Arròs i pasta, Llet i derivats, Iogurts, Olis, Vinagres, 
Conserves de peix, Conserves vegetals, Cereals i galetes, Xocolates, Cafè i infusions,
Begudes refrescants, Cerveses, Vins, Carns, Peixos, Fruites, Verdures, Congelats,
Neteja llar, Higiene personal, Mascotes, etc.

Respon NOMÉS en JSON sense cap text addicional:
{{
  "categories": [
    {{
      "categoria": "Arròs i pasta",
      "ids": [0, 5, 12]
    }}
  ]
}}"""

    return cridar_groq(prompt)

def agrupar_equivalents(productes, categoria):
    """Agrupa productes equivalents dins una categoria"""
    productes_text = "\n".join([
        f"{i}. [{p['supermercat']}] {p['producte']} {p['quantitat']} — {p['preu']}€"
        for i, p in enumerate(productes)
    ])

    prompt = f"""Tens productes de la categoria "{categoria}" de diferents supermercats:

{productes_text}

Agrupa els productes que són EXACTAMENT el mateix article (mateix tipus i mateixa quantitat aproximada).
No agruppis productes de mides molt diferents (ex: 1kg vs 500g són grups separats).
Productes de marca diferent però equivalents (ex: Hacendado vs Dia vs marca blanca) SÍ es poden agrupar.

Respon NOMÉS en JSON:
{{
  "grups": [
    {{
      "nom_normalitzat": "Arròs rodó 1kg",
      "ids": [0, 2, 3, 4]
    }}
  ]
}}"""

    return cridar_groq(prompt)

# FASE 1: Llegir tots els productes
print("\n📖 Llegint productes del Google Sheets...")
ws_preus = sheet.worksheet('Preus')
files = ws_preus.get_all_records()
print(f"✅ {len(files)} productes llegits")

# FASE 2: Categoritzar en lots de 50
print("\n🔍 Categoritzant productes amb Groq...")
mapa_categories = {}  # {index_producte: categoria}

mida_lot = 50
total_lots = (len(files) + mida_lot - 1) // mida_lot
print(f"  Total lots: {total_lots} (de {mida_lot} productes cada un)")

for i in range(0, len(files), mida_lot):
    lot = files[i:i+mida_lot]
    num_lot = i // mida_lot + 1
    print(f"  Lot {num_lot}/{total_lots}...")

    resultat = categoritzar_lot(lot)
    if resultat:
        for cat_info in resultat.get('categories', []):
            categoria = cat_info['categoria']
            for id_rel in cat_info.get('ids', []):
                id_abs = i + id_rel
                if id_abs < len(files):
                    mapa_categories[id_abs] = categoria

    # Pausa per no superar el límit de tokens
    time.sleep(12)

print(f"✅ {len(mapa_categories)} productes categoritzats")

# Recompte per categoria
categories_count = {}
for cat in mapa_categories.values():
    categories_count[cat] = categories_count.get(cat, 0) + 1

print("\n📊 Categories trobades:")
for cat, count in sorted(categories_count.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count} productes")

# FASE 3: Agrupar equivalents per categoria
print("\n🔗 Agrupant productes equivalents per categoria...")
tots_grups = []

categories_unicas = list(set(mapa_categories.values()))
for num_cat, categoria in enumerate(categories_unicas, 1):
    # Agafar productes d'aquesta categoria
    productes_cat = [
        {**files[idx], 'idx_original': idx}
        for idx, cat in mapa_categories.items()
        if cat == categoria
    ]

    print(f"  [{num_cat}/{len(categories_unicas)}] {categoria}: {len(productes_cat)} productes")

    if len(productes_cat) == 0:
        continue

    # Processar en sublots de 40
    for j in range(0, len(productes_cat), 40):
        sublot = productes_cat[j:j+40]
        resultat = agrupar_equivalents(sublot, categoria)

        if resultat:
            for grup in resultat.get('grups', []):
                nom = grup['nom_normalitzat']
                membres = []
                for id_rel in grup.get('ids', []):
                    if id_rel < len(sublot):
                        p = sublot[id_rel]
                        membres.append({
                            'nom_normalitzat': nom,
                            'categoria': categoria,
                            'supermercat': p['supermercat'],
                            'producte_original': p['producte'],
                            'preu': p['preu'],
                            'quantitat': p['quantitat'],
                        })
                if membres:
                    tots_grups.extend(membres)

        time.sleep(12)

print(f"✅ {len(tots_grups)} productes agrupats en {len(categories_unicas)} categories")

# FASE 4: Guardar al Google Sheets
print("\n💾 Guardant al Google Sheets...")
try:
    ws_norm = sheet.worksheet('Productes_Normalitzats')
    ws_norm.clear()
except:
    ws_norm = sheet.add_worksheet('Productes_Normalitzats', rows=50000, cols=10)

ws_norm.append_row(['nom_normalitzat', 'categoria', 'supermercat', 'producte_original', 'preu', 'quantitat', 'data'])
data = datetime.now().strftime('%Y-%m-%d %H:%M')
rows = []
for p in tots_grups:
    rows.append([
        p['nom_normalitzat'],
        p['categoria'],
        p['supermercat'],
        p['producte_original'],
        p['preu'],
        p['quantitat'],
        data
    ])

# Guardar en lots de 1000
for i in range(0, len(rows), 1000):
    ws_norm.append_rows(rows[i:i+1000])
    time.sleep(2)

print(f"✅ {len(rows)} files guardades a 'Productes_Normalitzats'")

print("\n" + "="*60)
print("✅ NORMALITZACIÓ COMPLETADA!")
print("="*60)
