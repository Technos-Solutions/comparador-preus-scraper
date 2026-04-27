import re
from collections import defaultdict
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Connectar Google Sheets
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws = sheet.worksheet('Preus')

print("📖 Llegint productes...")
files = ws.get_all_records()
print(f"✅ {len(files)} productes llegits")

# Diccionari de paraules clau en català/castellà
PARAULES_CLAU = {
    'llet': ['llet', 'leche', 'llet sencera', 'llet desnatada', 'llet semidesnatada'],
    'iogurt': ['iogurt', 'yogur', 'yogurt'],
    'arros': ['arros', 'arròs', 'arroz'],
    'pasta': ['pasta', 'macarrons', 'macarrones', 'espaguetis', 'fideus', 'fideos'],
    'cervesa': ['cervesa', 'cerveza', 'birra'],
    'vi': ['vi blanc', 'vi negre', 'vi rosat', 'vino tinto', 'vino blanco', 'vino rosado'],
    'cava': ['cava', 'cava brut'],
    'tonyina': ['tonyina', 'atun', 'atún'],
    'oli': ['oli d\'oliva', 'aceite de oliva', 'oli de girasol', 'aceite de girasol'],
    'ous': ['ous', 'huevos', 'huevo'],
    'pa': ['pa de motlle', 'pan de molde', 'pa integral'],
    'mantega': ['mantega', 'mantequilla'],
    'sucre': ['sucre', 'azucar', 'azúcar'],
    'cafe': ['cafe', 'café', 'cápsulas', 'capsules'],
    'tomàquet': ['tomàquet', 'tomate', 'tomàquet fregit', 'tomate frito'],
    'patates': ['patates fregides', 'patatas fritas'],
    'galetes': ['galetes', 'galletas'],
    'xocolata': ['xocolata', 'chocolate'],
    'detergent': ['detergent', 'detergente'],
    'lleixiu': ['lleixiu', 'lejia', 'lejía'],
}

def normalitzar_text(text):
    """Normalitza text per comparar"""
    text = text.lower()
    text = re.sub(r'[àáâä]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    return text

def trobar_categoria(nom_producte):
    """Troba la categoria d'un producte per paraules clau"""
    nom_norm = normalitzar_text(nom_producte)
    for categoria, paraules in PARAULES_CLAU.items():
        for paraula in paraules:
            if normalitzar_text(paraula) in nom_norm:
                return categoria
    return None

# Agrupar productes per categoria
grups = defaultdict(list)
sense_categoria = 0

for p in files:
    cat = trobar_categoria(p['producte'])
    if cat:
        grups[cat].append(p)
    else:
        sense_categoria += 1

print(f"\n📊 RESULTATS:")
print(f"  Productes categoritzats: {len(files) - sense_categoria}")
print(f"  Productes sense categoria: {sense_categoria}")
print(f"\n📦 CATEGORIES TROBADES:")
for cat, productes in sorted(grups.items(), key=lambda x: -len(x[1])):
    supermercats = set(p['supermercat'] for p in productes)
    print(f"  {cat}: {len(productes)} productes ({len(supermercats)} supermercats)")
    # Mostra exemple
    for p in productes[:2]:
        print(f"    [{p['supermercat']}] {p['producte']} — {p['preu']}€")
