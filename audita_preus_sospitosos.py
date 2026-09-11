# audita_preus_sospitosos.py — Script de només lectura, NO toca cap dada.
# Escaneja 'Comparacions_v2' buscant estalvis sospitosament grans (probablement
# errors de scraping/dades, no ofertes reals) i mostra les files originals de
# 'Preus' de cada cas per poder revisar-los manualment.
#
# Llindar configurable via variable d'entorn LLINDAR_PERCENTATGE (per defecte 60%).

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os

LLINDAR_PERCENTATGE = float(os.environ.get('LLINDAR_PERCENTATGE', '60'))

creds_dict = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')

ws_comp = sheet.worksheet('Comparacions_v2')
comparacions = ws_comp.get_all_records()
print(f"Total comparacions: {len(comparacions)}")
print(f"Llindar de sospita: estalvi > {LLINDAR_PERCENTATGE}%\n")

sospitosos = []
for c in comparacions:
    pct_text = str(c.get('Estalvi (%)', '')).replace('%', '').strip()
    try:
        pct = float(pct_text)
    except ValueError:
        continue
    if pct > LLINDAR_PERCENTATGE:
        sospitosos.append((pct, c))

sospitosos.sort(key=lambda x: -x[0])
print(f"Casos sospitosos trobats: {len(sospitosos)}\n")
print("=" * 70)

ws_cache = sheet.worksheet('Productes_Normalitzats')
cache = ws_cache.get_all_records()

ws_preus = sheet.worksheet('Preus')
preus = ws_preus.get_all_records()

SUPERMERCATS = ['Mercadona', 'Bon Àrea', 'Dia', 'Bon Preu / Esclat', 'Carrefour']

for pct, c in sospitosos:
    nom = c.get('Producte normalitzat')
    marca = c.get('Marca')
    print(f"⚠️  {pct}% d'estalvi — {nom} / {marca} ({c.get('Unitat')})")
    for sup in SUPERMERCATS:
        preu = c.get(sup, '')
        if preu not in ('', None):
            print(f"    {sup:<20} {preu}")
    print(f"    Més barat: {c.get('Supermercat més barat')}")

    # Buscar els noms originals que apunten a aquest producte normalitzat
    noms_originals = {
        r['nom_original'] for r in cache
        if str(r.get('nom_normalitzat', '')).strip() == str(nom).strip()
        and str(r.get('marca', '')).strip() == str(marca).strip()
    }
    files_originals = [p for p in preus if str(p.get('producte', '')).strip() in noms_originals]
    print(f"    Dades originals (Preus):")
    for p in files_originals:
        print(f"      [{p.get('supermercat')}] {p.get('producte')!r} — "
              f"preu={p.get('preu')!r} quantitat={p.get('quantitat')!r} envas={p.get('envas')!r}")
    print("-" * 70)

print(f"\n✅ Fet! {len(sospitosos)} casos sospitosos revisats.")
