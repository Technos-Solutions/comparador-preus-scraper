import re
from collections import defaultdict
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
    text = re.sub(r'[aaaa]', 'a', text)
    text = re.sub(r'[eeee]', 'e', text)
    text = re.sub(r'[iiii]', 'i', text)
    text = re.sub(r'[oooo]', 'o', text)
    text = re.sub(r'[uuuu]', 'u', text)
    text = re.sub(r'[c]', 'c', text)
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

PARAULES_CLAU = {
    'llet': [' llet ', ' leche '],
    'iogurt': [' iogurt ', ' yogur ', ' yogurt '],
    'arros': [' arros ', ' arroz '],
    'pasta': [' macarrons ', ' macarrones ', ' espaguetis ', ' fideus ', ' fideos ', ' lasanya ', ' lasana '],
    'cervesa': [' cervesa ', ' cerveza '],
    'vi': [' vi blanc', ' vi negre', ' vi rosat', ' vino tinto', ' vino blanco', ' vino rosado'],
    'cava': [' cava '],
    'tonyina': [' tonyina ', ' atun '],
    'oli oliva': [' oli d oliva', ' aceite de oliva'],
    'oli girasol': [' oli de girasol', ' aceite de girasol'],
    'ous': [' ous ', ' huevos '],
    'pa motlle': ['pa de motlle', 'pan de molde'],
    'mantega': [' mantega ', ' mantequilla '],
    'sucre': [' sucre blanc ', ' azucar '],
    'cafe': [' cafe molt', ' cafe soluble', ' cafe en capsules', ' cafe en capsulas', ' cafe en gra'],
    'tomaquet fregit': ['tomate frito', 'tomaquet fregit'],
    'patates fregides': ['patates fregides', 'patatas fritas'],
    'galetes': [' galetes ', ' galletas '],
    'xocolata': [' xocolata ', ' chocolate '],
    'detergent': [' detergent ', ' detergente '],
    'lleixiu': [' lleixiu ', ' lejia '],
    'aigua': [' agua mineral', ' agua con gas', ' agua sin gas', ' aigua '],
}

def trobar_categoria(nom_producte):
    nom_norm = normalitzar_text(nom_producte)
    nom_amb_espais = f' {nom_norm} '
    for categoria, paraules in PARAULES_CLAU.items():
        for paraula in paraules:
            if normalitzar_text(paraula) in nom_amb_espais:
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
print(f"\nCATEGORIES TROBADES:")
for cat, productes in sorted(grups.items(), key=lambda x: -len(x[1])):
    supermercats = set(p['supermercat'] for p in productes)
    print(f"  {cat}: {len(productes)} productes ({len(supermercats)} supermercats)")
    for p in productes[:2]:
        print(f"    [{p['supermercat']}] {p['producte']} - {p['preu']} EUR")
