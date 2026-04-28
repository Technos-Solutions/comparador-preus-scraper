import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from rapidfuzz import fuzz, process
import unicodedata
import re
from collections import defaultdict

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
    # Eliminar marques comercials i informació extra
    text = re.sub(r'\b(hacendado|dia|carrefour|bonpreu|bon area|esclat)\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Filtrar només llet per la prova
print("\nFiltrant productes de llet...")
llets = []
for p in files:
    nom = normalitzar_text(p['producte'])
    if nom.startswith('llet ') or nom.startswith('leche '):
        llets.append({
            'original': p['producte'],
            'normalitzat': nom,
            'supermercat': p['supermercat'],
            'preu': p['preu'],
            'quantitat': p['quantitat']
        })

print(f"{len(llets)} productes de llet trobats")

# Agrupar per similitud
print("\nAgrupant per similitud...")
grups = []
processats = set()

for i, p1 in enumerate(llets):
    if i in processats:
        continue
    
    grup = [p1]
    processats.add(i)
    
    for j, p2 in enumerate(llets):
        if j in processats or i == j:
            continue
        
        similitud = fuzz.token_sort_ratio(p1['normalitzat'], p2['normalitzat'])
        if similitud >= 75:
            grup.append(p2)
            processats.add(j)
    
    grups.append(grup)

# Mostrar grups amb més d'un supermercat
print(f"\nTotal grups: {len(grups)}")
print("\nGRUPS AMB MES D'UN SUPERMERCAT:")
grups_comparables = 0
for grup in sorted(grups, key=lambda x: -len(x)):
    supermercats = set(p['supermercat'] for p in grup)
    if len(supermercats) > 1:
        grups_comparables += 1
        preus = sorted(grup, key=lambda x: float(x['preu']) if x['preu'] else 999)
        print(f"\n--- {grup[0]['original']} ---")
        for p in preus:
            print(f"  [{p['supermercat']}] {p['original']} - {p['preu']} EUR")

print(f"\nTotal grups comparables: {grups_comparables}")
