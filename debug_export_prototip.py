# debug_export_prototip.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets.
# Exporta al registre (JSON) les dades reals per al prototip visual de l'aplicacio:
# Comparacions_v3 sencera, les marques blanques confirmades i els canvis de l'historic
# (ultima fila i anterior de cada producte). No escriu res.

import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    comparacions = sheet.worksheet('Comparacions_v3').get_all_values(value_render_option='UNFORMATTED_VALUE')
    marques = [f for f in sheet.worksheet('Marques_Blanques').get_all_records()
               if str(f.get('estat', '')).strip().lower() == 'confirmada']
    # Historic: per a cada producte amb 2 o mes files, l'ultima i l'anterior (canvis de la setmana)
    historic = gspread.authorize(creds).open('Comparador_Preus_Historic').worksheet('Historic_Preus') \
        .get_all_values(value_render_option='UNFORMATTED_VALUE')
    per_producte = {}
    for fila in historic[1:]:
        per_producte.setdefault((fila[1], fila[2]), []).append(fila)
    canvis = [[f[-2], f[-1]] for f in per_producte.values() if len(f) >= 2]
    print('###INICI_JSON###')
    print(json.dumps({'comparacions': comparacions, 'canvis': canvis,
                      'marques': [[f['marca'], f['supermercat']] for f in marques]},
                     ensure_ascii=False, separators=(',', ':')))
    print('###FI_JSON###')
    print(f"Comparacions: {len(comparacions) - 1} | canvis de l'historic: {len(canvis)} | "
          f"marques blanques confirmades: {len(marques)}")


if __name__ == '__main__':
    main()
