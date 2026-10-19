# debug_marques_pendents.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets,
# no crida Gemini ni escriu res.
#
# Llista les marques "pendent" de Marques_Blanques amb el nombre de productes i
# exemples de noms originals (Productes_Atributs), per decidir si son marca blanca
# (marca propia o exclusiva del supermercat) o de fabricant.

import json
import os
from collections import defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from normalitzador_v3 import sense_accents


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    atributs = sheet.worksheet('Productes_Atributs').get_all_records()
    marques = sheet.worksheet('Marques_Blanques').get_all_records()
    per_marca = defaultdict(list)
    for a in atributs:
        per_marca[(str(a.get('supermercat', '')).strip(), sense_accents(a.get('marca')))].append(
            f"{a.get('nom_original')} [{a.get('categoria')}]")
    pendents = [f for f in marques if str(f.get('estat', '')).strip().lower() == 'pendent']
    print(f"Marques_Blanques: {len(marques)} files | pendents: {len(pendents)}\n")
    for i, f in enumerate(marques):
        if str(f.get('estat', '')).strip().lower() != 'pendent':
            continue
        s = str(f.get('supermercat', '')).strip()
        noms = per_marca.get((s, sense_accents(f.get('marca'))), [])
        print(f"### fila {i + 2} | {s} | {f.get('marca')} | {len(noms)} productes")
        for n in noms[:4]:
            print(f"     {n[:110]}")


if __name__ == '__main__':
    main()
