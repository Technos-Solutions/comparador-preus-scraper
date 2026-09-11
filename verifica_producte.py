# verifica_producte.py — Script de només lectura per investigar un producte concret
# Mostra les files originals de 'Preus' que s'amaguen darrere d'una entrada de 'Comparacions_v2',
# per detectar errors de dades o de conversió d'unitats.

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os

NOM_NORMALITZAT_BUSCAT = 'oli d\'oliva verge extra'
MARCA_BUSCADA = 'Carbonell'

creds_dict = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')

# 1. Trobar tots els noms_originals que apunten a aquest producte normalitzat
ws_cache = sheet.worksheet('Productes_Normalitzats')
cache = ws_cache.get_all_records()
noms_originals = [
    r['nom_original'] for r in cache
    if str(r.get('nom_normalitzat', '')).strip() == NOM_NORMALITZAT_BUSCAT
    and str(r.get('marca', '')).strip() == MARCA_BUSCADA
]
print(f"Noms originals trobats per '{NOM_NORMALITZAT_BUSCAT}' / {MARCA_BUSCADA}: {len(noms_originals)}")
for n in noms_originals:
    print(f"  - {n!r}")
print()

# 2. Buscar aquests noms a 'Preus' i mostrar les dades crues
ws_preus = sheet.worksheet('Preus')
preus = ws_preus.get_all_records()
noms_set = set(noms_originals)

trobats = [p for p in preus if str(p.get('producte', '')).strip() in noms_set]
print(f"Files trobades a 'Preus': {len(trobats)}\n")
for p in trobats:
    print(f"  Producte:     {p.get('producte')!r}")
    print(f"  Marca:        {p.get('marca')!r}")
    print(f"  Supermercat:  {p.get('supermercat')!r}")
    print(f"  Preu:         {p.get('preu')!r}")
    print(f"  Quantitat:    {p.get('quantitat')!r}")
    print(f"  Envas:        {p.get('envas')!r}")
    print(f"  Data:         {p.get('data')!r}")
    print()
