import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from rapidfuzz import fuzz
import unicodedata
import re
from collections import defaultdict
import requests
import time

creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws = sheet.worksheet('Preus')

print("Llegint productes...")
files = ws.get_all_records()
print(f"{len(files)} productes llegits")

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Diccionari de traduccions catala/castella -> castella normalitzat
TRADUCCIONS = {
    'llet sencera': 'leche entera',
    'llet semidesnatada': 'leche semidesnatada',
    'llet desnatada': 'leche desnatada',
    'llet sense lactosa': 'leche sin lactosa',
    'llet condensada': 'leche condensada',
    'llet evaporada': 'leche evaporada',
    'llet en pols': 'leche en polvo',
    'llet': 'leche',
    'arros rodó': 'arroz redondo',
    'arros llarg': 'arroz largo',
    'arros integral': 'arroz integral',
    'arros basmati': 'arroz basmati',
    'arros bomba': 'arroz bomba',
    'arros': 'arroz',
    'iogurt natural': 'yogur natural',
    'iogurt desnatat': 'yogur desnatado',
    'iogurt grec': 'yogur griego',
    'iogurt': 'yogur',
    'cervesa sense alcohol': 'cerveza sin alcohol',
    'cervesa negra': 'cerveza negra',
    'cervesa rossa': 'cerveza rubia',
    'cervesa': 'cerveza',
    'galetes': 'galletas',
    'xocolata negra': 'chocolate negro',
    'xocolata amb llet': 'chocolate con leche',
    'xocolata': 'chocolate',
    'mantega': 'mantequilla',
    'sucre blanc': 'azucar blanco',
    'sucre': 'azucar',
    'ous': 'huevos',
    'oli d oliva verge extra': 'aceite de oliva virgen extra',
    'oli d oliva': 'aceite de oliva',
    'oli de girasol': 'aceite de girasol',
    'tonyina': 'atun',
    'detergent': 'detergente',
    'lleixiu': 'lejia',
    'aigua amb gas': 'agua con gas',
    'aigua sense gas': 'agua sin gas',
    'aigua mineral': 'agua mineral',
    'aigua': 'agua',
    'pa de motlle': 'pan de molde',
    'pa integral': 'pan integral',
    'sencer': 'entero',
    'sencera': 'entera',
    'sense lactosa': 'sin lactosa',
    'desnatat': 'desnatado',
    'desnatada': 'desnatada',
    'semidesnatat': 'semidesnatado',
    'semidesnatada': 'semidesnatada',
    'rodó': 'redondo',
    'llarg': 'largo',
    'integral': 'integral',
    'paq': 'pack',
    'u.': 'unidades',
    'bric': 'brik',
}

def normalitzar_text(text):
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

def traduir_producte(nom):
    nom = normalitzar_text(nom)
    # Eliminar marques comercials
    for marca in ['hacendado', 'bonpreu', 'bon area', 'esclat', 'carrefour', 'dia lactea']:
        nom = re.sub(r'\b' + marca + r'\b', '', nom)
    # Aplicar traduccions de mes llargues a mes curtes
    for cat, esp in sorted(TRADUCCIONS.items(), key=lambda x: -len(x[0])):
        nom = re.sub(r'\b' + normalitzar_text(cat) + r'\b', esp, nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

def cridar_groq_comparar(p1, p2):
    """Crida Groq per verificar si dos productes son el mateix"""
    prompt = f"""Són exactament el mateix producte (mateix tipus i mateixa quantitat aproximada)?

Producte 1: {p1['producte']} ({p1['supermercat']}) - {p1['preu']}EUR
Producte 2: {p2['producte']} ({p2['supermercat']}) - {p2['preu']}EUR

Respon NOMÉS amb: SI o NO"""

    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 10
            },
            timeout=10
        )
        resultat = response.json()
        resposta = resultat['choices'][0]['message']['content'].strip().upper()
        return 'SI' in resposta
    except:
        return False

# Filtrar llet per la prova
print("\nFiltrant productes de llet...")
llets = []
for p in files:
    nom = normalitzar_text(p['producte'])
    if nom.startswith('llet ') or nom.startswith('leche '):
        llets.append(p)

print(f"{len(llets)} productes de llet trobats")

# Agrupar per similitud amb text traduit
print("\nAgrupant per similitud (amb traduccio)...")
grups = []
processats = set()
casos_dubtosos = 0
casos_groq = 0

for i, p1 in enumerate(llets):
    if i in processats:
        continue

    grup = [p1]
    processats.add(i)
    nom1_traduit = traduir_producte(p1['producte'])

    for j, p2 in enumerate(llets):
        if j in processats or i == j:
            continue

        nom2_traduit = traduir_producte(p2['producte'])
        similitud = fuzz.token_sort_ratio(nom1_traduit, nom2_traduit)

        if similitud >= 85:
            # Alta similitud -> mateix producte directament
            grup.append(p2)
            processats.add(j)
        elif similitud >= 60:
            # Similitud dubtosa -> preguntem a Groq
            casos_dubtosos += 1
            if casos_groq < 20:  # Limitem crides a Groq per la prova
                es_mateix = cridar_groq_comparar(p1, p2)
                casos_groq += 1
                time.sleep(1)
                if es_mateix:
                    grup.append(p2)
                    processats.add(j)

    grups.append(grup)

print(f"Casos dubtosos detectats: {casos_dubtosos}")
print(f"Crides a Groq: {casos_groq}")

# Mostrar grups comparables
print(f"\nTotal grups: {len(grups)}")
print("\nGRUPS AMB MES D'UN SUPERMERCAT:")
grups_comparables = 0
for grup in sorted(grups, key=lambda x: -len(x)):
    supermercats = set(p['supermercat'] for p in grup)
    if len(supermercats) > 1:
        grups_comparables += 1
        preus = sorted(grup, key=lambda x: float(str(x['preu']).replace(',', '.')) if x['preu'] else 999)
        print(f"\n--- {grup[0]['producte']} ---")
        for p in preus:
            traduit = traduir_producte(p['producte'])
            print(f"  [{p['supermercat']}] {p['producte']} ({traduit}) - {p['preu']} EUR")

print(f"\nTotal grups comparables: {grups_comparables}")
print("\nPRODUCTES DE BON PREU AMB 'llet' o 'leche':")
for p in files:
    sup = p['supermercat']
    nom = normalitzar_text(p['producte'])
    if sup == 'Bon Preu / Esclat' and ('llet' in nom or 'leche' in nom):
        print(f"  {p['producte']}")
