# debug_export_prototip.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets.
# Exporta al registre (JSON) les dades reals per al prototip visual de l'aplicacio:
# Comparacions_v3 sencera i les marques blanques confirmades. No escriu res.

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
    print('###INICI_JSON###')
    print(json.dumps({'comparacions': comparacions,
                      'marques': [[f['marca'], f['supermercat']] for f in marques]},
                     ensure_ascii=False, separators=(',', ':')))
    print('###FI_JSON###')
    print(f"Comparacions: {len(comparacions) - 1} | marques blanques confirmades: {len(marques)}")


if __name__ == '__main__':
    main()
