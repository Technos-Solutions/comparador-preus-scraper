import re
from collections import defaultdict
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import unicodedata

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

def normalitzar_text(text):
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

INICI_PRODUCTE = {
    'llet ': 'llet',
    'leche ': 'llet',
    'iogurt': 'iogurt',
    'yogur': 'iogurt',
    'arroz': 'arros',
    'arros': 'arros',
    'cerveza': 'cervesa',
    'cervesa': 'cervesa',
    'vino tinto': 'vi',
    'vino blanco': 'vi',
    'vino rosado': 'vi',
    'vi negre': 'vi',
    'vi blanc': 'vi',
    'vi rosat': 'vi',
    'cava ': 'cava',
    'atun': 'tonyina',
    'tonyina': 'tonyina',
    'aceite de oliva': 'oli oliva',
    'aceite de girasol': 'oli girasol',
    'huevos': 'ous',
    'ous ': 'ous',
    'pan de molde': 'pa motlle',
    'pa de motlle': 'pa motlle',
    'mantequilla': 'mantega',
    'mantega': 'mantega',
    'azucar': 'sucre',
    'sucre': 'sucre',
    'detergente': 'detergent',
    'detergent ': 'detergent',
    'lejia': 'lleixiu',
    'lleixiu': 'lleixiu',
    'agua mineral': 'aigua',
    'agua con gas': 'aigua',
    'agua sin gas': 'aigua',
    'galletas': 'galetes',
    'galetes': 'galetes',
    'chocolate': 'xocolata',
    'xocolata': 'xocolata',
    'patatas fritas': 'patates',
    'patates fregides': 'patates',
    'tomate frito': 'tomaquet',
    'tomaquet fregit': 'tomaquet',
    'cafe en': 'cafe',
    'cafe molt': 'cafe',
    'macarrones': 'pasta',
    'macarrons': 'pasta',
    'espaguetis': 'pasta',
    'fideos ': 'pasta',
    'fideus ': 'pasta',
    'lasana': 'pasta',
    'lasanya': 'pasta',
}

def trobar_categoria(nom_producte):
    nom_norm = normalitzar_text(nom_producte)
    for inici, categoria in INICI_PRODUCTE.items():
        if nom_norm.startswith(normalitzar_text(inici)):
            return categoria
    return None

grups = defaultdict(list)
sense_categoria = 0

for p in files:
    cat = trobar_categoria(p['producte'])
    if cat:
        grups[cat].append(p)
    else:
        sense_categoria += 1

print(f"\nRESULTATS:")
print(f"  Productes categoritzats: {len(files) - sense_categoria}")
print(f"  Productes sense categoria: {sense_categoria}")
print(f"\nCATEGORIES:")
for cat, productes in sorted(grups.items(), key=lambda x: -len(x[1])):
    supermercats = set(p['supermercat'] for p in productes)
    print(f"  {cat}: {len(productes)} productes ({len(supermercats)} supermercats)")
    for p in productes[:2]:
        print(f"    [{p['supermercat']}] {p['producte']} - {p['preu']} EUR")
        # Analitzar quants productes tenim per supermercat al total
print("\nPRODUCTES PER SUPERMERCAT (total):")
supermercats_total = defaultdict(int)
for p in files:
    supermercats_total[p['supermercat']] += 1
for sup, count in sorted(supermercats_total.items(), key=lambda x: -x[1]):
    print(f"  {sup}: {count} productes")

# Analitzar quants productes tenim per supermercat a cada categoria
print("\nPRODUCTES PER SUPERMERCAT A CATEGORIA 'llet':")
for p in grups.get('llet', []):
    print(f"  [{p['supermercat']}] {p['producte']}")

print("\nPRODUCTES PER SUPERMERCAT A CATEGORIA 'arros':")
for p in grups.get('arros', []):
    print(f"  [{p['supermercat']}] {p['producte']}")
