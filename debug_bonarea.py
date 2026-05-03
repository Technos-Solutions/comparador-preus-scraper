# Debug Normalitzador Mòdul 1 - Extreure marca i normalitzar nom
# Prova amb llet/leche desnatada/semidesnatada de 1L

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import re

# Connexió a Google Sheets
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws = sheet.worksheet('Preus')

print("✅ Connectat a Google Sheets")

files = ws.get_all_records()

# Filtrar només llet/leche (no iogurts, bífidus, formatge...)
PARAULES_LLET = ['leche ', 'llet ']
EXCLOURE = ['yogur', 'iogurt', 'bífidus', 'bifidus', 'queso', 'formatge',
            'bebida', 'condensada', 'polvo', 'pols', 'fermentada', 'kéfir', 'quefir']

productes = []
for f in files:
    nom = str(f.get('producte', '')).lower()
    if any(p in nom for p in PARAULES_LLET):
        if not any(e in nom for e in EXCLOURE):
            productes.append(f)

print(f"Total llets trobades: {len(productes)}\n")

# --- MÒDUL 1: Extreure marca i normalitzar nom ---

# Marques conegudes (extretes dels noms de BonPreu en MAJÚSCULES)
MARQUES = [
    'asturiana', 'central lechera asturiana', 'pascual', 'puleva', 'ato',
    'letona', 'kaiku', 'lauki', 'celta', 'covap', 'president', 'président',
    'rio', 'río', 'madriz', 'bonpreu', 'verntallat', 'llet nostra',
    'terra i tast', 'latorre', 'la torre', 'el castillo', 'castillo',
    'saer brau', 'gaza', 'dia láctea', 'hacendado', 'ato natura',
    'puleva omega3', 'puleva omega 3', 'kaiku s/lactosa'
]

# Ordenar per longitud descendent (per trobar primer les més llargues)
MARQUES = sorted(MARQUES, key=len, reverse=True)

def extreure_marca(nom):
    nom_lower = nom.lower().strip()
    
    # 1. BonPreu: paraules en MAJÚSCULES al davant
    match = re.match(r'^([A-ZÀÁÈÉÍÏÒÓÚÜÇ][A-ZÀÁÈÉÍÏÒÓÚÜÇ0-9/\s\-\.]+?)\s+[a-z]', nom)
    if match:
        marca = match.group(1).strip().title()
        nom_net = nom[len(match.group(1)):].strip()
        return marca, nom_net
    
    # 2. Altres supermercats: buscar marca coneguda al nom
    for marca in MARQUES:
        if marca in nom_lower:
            nom_net = re.sub(re.escape(marca), '', nom_lower, flags=re.IGNORECASE).strip()
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            return marca.title(), nom_net
    
    return '', nom

def normalitzar_nom(nom):
    nom = nom.lower()
    # Treure format envàs (brik, botella, ampolla, cartró, pack...)
    nom = re.sub(r'\b(brik|botella|ampolla|cartró|cartro|pack|envàs|envas|en cartró|en ampolla)\b', '', nom)
    # Treure mida envàs (1 l., 1,5 l, 6 x 1 L...)
    nom = re.sub(r'\d+[\s,.]?\d*\s*(x\s*)?\d*[\s,.]?\d*\s*(l|ml|kg|g|cl)\b\.?', '', nom)
    # Treure puntuació sobrera
    nom = re.sub(r'[.,;:]', '', nom)
    # Normalitzar espais
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

# Processar i mostrar resultats
print("=" * 90)
print(f"{'SUPERMERCAT':<20} {'MARCA':<25} {'NOM NORMALITZAT':<35} {'PREU':>6} {'QUANT':>8}")
print("=" * 90)

for p in productes:
    nom_original = p.get('producte', '')
    sup = p.get('supermercat', '')
    preu = p.get('preu', '')
    quant = p.get('quantitat', '')
    
    marca, nom_net = extreure_marca(nom_original)
    nom_normalitzat = normalitzar_nom(nom_net)
    
    print(f"{sup:<20} {marca:<25} {nom_normalitzat:<35} {str(preu):>6}€ {str(quant):>8}")
