# mostra_exemples.py — Script de només lectura per mostrar exemples de 'Comparacions_v2'
# Útil per veure com queden els productes normalitzats i comparats entre supermercats.

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os
from collections import defaultdict

creds_dict = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')

ws = sheet.worksheet('Comparacions_v2')
files = ws.get_all_records()
print(f"Total files a Comparacions_v2: {len(files)}\n")

per_categoria = defaultdict(list)
for f in files:
    per_categoria[f.get('Categoria', '')].append(f)

# 2 exemples per categoria, per tenir varietat
for cat in sorted(per_categoria.keys()):
    exemples = per_categoria[cat][:2]
    for f in exemples:
        print(f"── {cat} ──")
        print(f"  Producte: {f.get('Producte normalitzat')} | Marca: {f.get('Marca')} | Unitat: {f.get('Unitat')}")
        for sup in ['Mercadona', 'Bon Àrea', 'Dia', 'Bon Preu / Esclat', 'Carrefour']:
            preu = f.get(sup, '')
            if preu not in ('', None):
                print(f"    {sup:<20} {preu}")
        print(f"  Més barat: {f.get('Supermercat més barat')} | Estalvi: {f.get('Estalvi')} ({f.get('Estalvi (%)')})")
        print()
