# Debug Normalitzador Mòdul 1 - Filtre millorat per llet per beure
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import re

creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws = sheet.worksheet('Preus')

print("✅ Connectat a Google Sheets")
files = ws.get_all_records()

# Paraules que han d'estar al nom
INCLOU = ['leche ', 'llet ']

# Paraules que exclouen el producte
EXCLOU = [
    'yogur', 'iogurt', 'bífidus', 'bifidus', 'queso', 'formatge',
    'bebida', 'condensada', 'polvo', 'pols', 'fermentada', 'kéfir', 'quefir',
    'chocolate', 'xocolata', 'café', 'cafè', 'cacao', 'cacau',
    'solar', 'corporal', 'facial', 'limpiadora', 'netejadora', 'aftersun',
    'infantil', 'lactant', 'creixement', 'crecimiento', 'materna',
    'galleta', 'barrita', 'cereal', 'arroz', 'arròs', 'natilla',
    'helado', 'gelat', 'mousse', 'flan', 'flam',
    'gel', 'jabón', 'sabó', 'dentífric', 'champú', 'xampú',
    'salchicha', 'puré', 'pan ', 'pa ', 'bollería', 'bizcocho',
    'fruta', 'fruita', 'zumo', 'suc amb llet',
    'dulce de leche', 'dolç de llet',
    'nata', 'evaporada', 'crema al cacao',
]

productes = []
for f in files:
    nom = str(f.get('producte', '')).lower()
    if any(p in nom for p in INCLOU):
        if not any(e in nom for e in EXCLOU):
            productes.append(f)

print(f"Total llets per beure: {len(productes)}\n")

# Marques conegudes
MARQUES = sorted([
    'central lechera asturiana', 'asturiana', 'pascual', 'puleva omega3',
    'puleva omega 3', 'puleva', 'kaiku s/lactosa', 'kaiku', 'ato natura',
    'ato', 'letona', 'lauki', 'celta', 'covap', 'president', 'président',
    'rio', 'río', 'madriz', 'bonpreu', 'verntallat', 'llet nostra',
    'terra i tast', 'latorre', 'la torre', 'el castillo', 'castillo',
    'dia láctea', 'hacendado', 'gaza', 'la cántara', 'celta'
], key=len, reverse=True)

def extreure_marca(nom):
    nom_lower = nom.lower().strip()
    # BonPreu: MAJÚSCULES al davant
    match = re.match(r'^([A-ZÀÁÈÉÍÏÒÓÚÜÇ][A-ZÀÁÈÉÍÏÒÓÚÜÇ0-9/\s\-\.]+?)\s+[a-z]', nom)
    if match:
        marca = match.group(1).strip().title()
        nom_net = nom[len(match.group(1)):].strip()
        return marca, nom_net
    # Altres: buscar marca coneguda
    for marca in MARQUES:
        if marca in nom_lower:
            nom_net = re.sub(re.escape(marca), '', nom_lower, flags=re.IGNORECASE).strip()
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            return marca.title(), nom_net
    return '', nom.lower()

def normalitzar_nom(nom):
    nom = nom.lower()
    nom = re.sub(r'\b(brik|botella|ampolla|cartró|cartro|pack|en cartró|en ampolla|uht)\b', '', nom)
    nom = re.sub(r'\d+[\s,.]?\d*\s*(x\s*)?\d*[\s,.]?\d*\s*(l|ml|kg|g|cl)\b\.?', '', nom)
    nom = re.sub(r'\b(bric|brick|format|viatge|paq|paq\.|paquet)\b', '', nom)
    nom = re.sub(r'[.,;:]', '', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

# Mostrar resultats
print("=" * 90)
print(f"{'SUPERMERCAT':<20} {'MARCA':<25} {'NOM NORMALITZAT':<35} {'PREU':>6} {'QUANT':>10}")
print("=" * 90)

for p in productes:
    nom_original = p.get('producte', '')
    sup = p.get('supermercat', '')
    preu = p.get('preu', '')
    quant = p.get('quantitat', '')
    marca, nom_net = extreure_marca(nom_original)
    nom_normalitzat = normalitzar_nom(nom_net)
    print(f"{sup:<20} {marca:<25} {nom_normalitzat:<35} {str(preu):>6}€ {str(quant):>10}")
