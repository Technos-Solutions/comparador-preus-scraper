# Debug Normalitzador Mòdul 1 - Filtre v6
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

# Ha de contenir una d'aquestes paraules
INCLOU = ['leche ', 'llet ']

# I una d'aquestes per ser llet de debò
TIPUS_LLET = ['entera', 'sencera', 'desnat', 'semidenat', 'semidesnat',
              'fresca', 'sense lactosa', 'sin lactosa', 'calcio', 'calci',
              'omega 3', 'ecològica', 'ecológica', 'barista', 'proteina', 'proteïna']

EXCLOU = [
    'yogur', 'iogurt', 'bífidus', 'bifidus', 'queso', 'formatge',
    'bebida', 'condensada', 'polvo', 'pols', 'fermentada', 'kéfir', 'quefir',
    'chocolate', 'xocolata', 'café', 'cafè', 'cacao', 'cacau',
    'galleta', 'barrita', 'cereal', 'arroz', 'arròs', 'natilla',
    'helado', 'gelat', 'mousse', 'flan', 'flam', 'dulce de leche', 'dolç de llet',
    'bollería', 'bizcocho', 'pan ', 'pa ', 'pastel', 'brownie',
    'frita', 'frito', 'panes', 'bollito', 'phoskito',
    'salchicha', 'campof',
    'solar', 'corporal', 'facial', 'limpiadora', 'netejadora', 'aftersun',
    'fps', 'spf', 'fp-', 'protector', 'protectora', 'hidratant', 'hidratante',
    'gel ', 'jabón', 'sabó', 'dentífric', 'champú', 'xampú', 'paper ',
    'scottex', 'desenredant', 'reafirmant', 'delial', 'denenes', 'nivea', 'ecran',
    'bronceja', 'bronzeja',
    'gat', 'gos', 'felí', 'canin', 'felix ', 'youwup', 'yowup',
    'ametll', 'coco', 'avena', 'civada', 'soja', 'vegetal',
    'suc amb llet', 'suc de fruites', 'zumo', 'fruta ', 'fruita ',
    'nata', 'evaporada', 'crema ', 'rotllet', 'farcellet',
    'puré', 'batut', 'batido',
    'infantil', 'lactant', 'creixement', 'crecimiento', 'materna',
    'almirón', 'nativa', 'nestlé junior', 'blemil', 'nidina', 'blédina',
    'llibre', 'barcanova', 'bullet ', 'vi rosat',
    'càpsula', 'cápsula', 'dolce gusto',
    'folic', 'nous',
]

productes = []
for f in files:
    nom = str(f.get('producte', '')).lower()
    if any(p in nom for p in INCLOU):
        if any(t in nom for t in TIPUS_LLET):
            if not any(e in nom for e in EXCLOU):
                productes.append(f)

print(f"Total llets per beure: {len(productes)}\n")

# ── Marques ordenades de més llarga a més curta (evita solapaments) ──────────
MARQUES = sorted([
    'central lechera asturiana', 'asturiana',
    'pascual calci', 'pascual',
    'puleva omega3', 'puleva omega 3', 'puleva max', 'puleva',
    'kaiku s/lactosa', 'kaiku',
    'ato natura', 'ato',
    'letona', 'lauki', 'celta', 'covap',
    'president', 'président',
    'rio', 'río', 'madriz',
    'bonpreu', 'verntallat', 'llet nostra', 'terra i tast',
    'latorre', 'la torre', 'el castillo', 'castillo',
    'dia láctea', 'dia lactea',
    'hacendado',
    'gaza', 'la cántara',
    # marques pròpies supermercat
    'ifa',
    'carrefour bio', 'carrefour',
    'el buen pastor',
], key=len, reverse=True)

def extreure_marca(nom):
    nom_lower = nom.lower().strip()
    # BonPreu: prefix en MAJÚSCULES seguit d'una paraula en minúscules
    match = re.match(r'^([A-ZÀÁÈÉÍÏÒÓÚÜÇ][A-ZÀÁÈÉÍÏÒÓÚÜÇ0-9/\s\-\.]+?)\s+[a-z]', nom)
    if match:
        marca = match.group(1).strip().title()
        nom_net = nom[len(match.group(1)):].strip()
        return marca, nom_net
    # Resta de supermercats: buscar marca coneguda al nom
    for marca in MARQUES:
        if marca in nom_lower:
            nom_net = re.sub(re.escape(marca), '', nom_lower, flags=re.IGNORECASE).strip()
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            return marca.title(), nom_net
    return '', nom.lower()

# ── Normalització ─────────────────────────────────────────────────────────────
# Mapa català → castellà per unificar tipus de llet
TRADUCCIONS = {
    'llet': 'leche',
    'sencera': 'entera',
    'desnatada': 'desnatada',
    'semidesnatada': 'semidesnatada',
    'sense lactosa': 'sin lactosa',
    'ecològica': 'ecológica',
    'proteïna': 'proteina',
    'calci': 'calcio',
    'fresca': 'fresca',
    'barista': 'barista',
}

def normalitzar_nom(nom):
    nom = nom.lower()
    # Treure informació de conservació entre parèntesis
    nom = re.sub(r'\(.*?\)', '', nom)
    # Treure format de pack: "3 u de", "de 6 brics de", "6 briks de", etc.
    nom = re.sub(r'\d+\s*u\s*(de\s*)?', '', nom)
    nom = re.sub(r'de\s+\d+\s*(bric|brik|brick)s?\s*(de\s*)?', '', nom, flags=re.IGNORECASE)
    # Treure envasos i formats
    nom = re.sub(r'\b(brik|bric|brick|botella|ampolla|cartró|cartro|pack|en cartró|en ampolla|uht)\b', '', nom)
    # Treure mides/quantitats (1l, 1.5l, 200ml, 6x1l, etc.)
    nom = re.sub(r'\d+[\s,.]?\d*\s*(x\s*)?\d*[\s,.]?\d*\s*(l|ml|kg|g|cl)\b\.?', '', nom)
    # Treure altres paraules de format
    nom = re.sub(r'\b(bric|brick|format|viatge|paq\.?|paquet|km0|km|a2)\b', '', nom)
    # Treure "de" sobrant al final
    nom = re.sub(r'\bde\b\s*$', '', nom)
    nom = re.sub(r'[.,;:()\[\]]', '', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    # Traduir català → castellà per unificar
    for cat, cas in TRADUCCIONS.items():
        nom = re.sub(r'\b' + re.escape(cat) + r'\b', cas, nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

# ── Imprimir resultats ────────────────────────────────────────────────────────
print("=" * 100)
print(f"{'SUPERMERCAT':<20} {'MARCA':<28} {'NOM NORMALITZAT':<40} {'PREU':>6} {'QUANT':>12}")
print("=" * 100)

for p in productes:
    nom_original = p.get('producte', '')
    sup = p.get('supermercat', '')
    preu = p.get('preu', '')
    quant = p.get('quantitat', '')
    envas = p.get('envas', '')
    marca, nom_net = extreure_marca(nom_original)
    nom_normalitzat = normalitzar_nom(nom_net)
    print(f"{sup:<20} {marca:<28} {nom_normalitzat:<40} {str(preu):>6}€ {str(quant)+' '+str(envas):>12}")
