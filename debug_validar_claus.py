# debug_validar_claus.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu enlloc)
# i no crida Gemini. Valida normalitzador_v3.comparar amb les claus noves (12/11: sense puntuacio i
# marques comercials sense categoria) contra Comparacions_v3 del full (calculat dilluns amb les velles).
import json
import os
from collections import Counter

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = nv3.llegir_preus(sheet)
    atributs = nv3.llegir_atributs(sheet.worksheet('Productes_Atributs'))
    marques = nv3.MarquesBlanques(sheet.worksheet('Marques_Blanques').get_all_records(), atributs)
    full = sheet.worksheet('Comparacions_v3').get_all_values()[1:]
    nou = nv3.comparar(preus, atributs, marques)
    print(f"Full (dilluns): {len(full)} {dict(Counter(f[0] for f in full))} | Revisar {sum(1 for f in full if f[-2])}")
    print(f"Codi nou:       {len(nou)} {dict(Counter(f[0] for f in nou))} | Revisar {sum(1 for f in nou if f[-2])}")
    print(f"Files sense categoria: {sum(1 for f in nou if not f[1])} | columnes per fila: {Counter(len(f) for f in nou)}")
    print(f"Pendents a descartar (marques blanques): {len(marques.pendents_a_descartar())}")
    print("\nDr. Oetker (codi nou):")
    for f in nou:
        if 'oetker' in f[2].lower():
            preus_s = ' | '.join(f"{s[:9]} {v}" for s, v in zip(nv3.SUPERMERCATS, f[6:11]) if v != '')
            print(f"   {f[1]} | {f[3]} {f[4]} {f[5]} | {preus_s} | barat {f[12]}")


if __name__ == '__main__':
    main()
