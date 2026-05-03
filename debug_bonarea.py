# Debug Normalitzador - Buscar "leche desnatada" a tots els supermercats
# Executa via GitHub Actions per tenir accés a GOOGLE_CREDENTIALS

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# Connexió a Google Sheets
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
sheet = client.open_by_key(SPREADSHEET_ID)
ws = sheet.worksheet('Preus')

print("✅ Connectat a Google Sheets")
print("🔍 Buscant 'leche desnatada' / 'llet desnatada'...\n")

# Llegir totes les dades
files = ws.get_all_records()
print(f"Total productes: {len(files)}")

# Filtrar productes que continguin 'desnat' al nom
paraules_clau = ['desnat', 'descrema']
resultats = []
for f in files:
    nom = str(f.get('producte', '')).lower()
    if any(p in nom for p in paraules_clau):
        resultats.append(f)

print(f"Productes trobats: {len(resultats)}\n")
print("=" * 80)

# Mostrar resultats agrupats per supermercat
supermercats = {}
for r in resultats:
    sup = r.get('supermercat', 'Desconegut')
    if sup not in supermercats:
        supermercats[sup] = []
    supermercats[sup].append(r)

for sup, prods in sorted(supermercats.items()):
    print(f"\n🏪 {sup} ({len(prods)} productes):")
    print("-" * 60)
    for p in prods:
        print(f"  · {p.get('producte', '')} | {p.get('preu', '')}€ | {p.get('quantitat', '')}")
