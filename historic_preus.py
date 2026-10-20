# historic_preus.py — Historic de preus a la pestanya Historic_Preus (des del 20/10/2026)
#
# Per no omplir el Google Sheet (limit de 10 milions de cel·les) nomes es desa una fila
# quan un producte apareix per primer cop o quan li canvia el preu:
#   data | supermercat | producte | preu
# El preu d'un producte en una data qualsevol es el de l'ultima fila anterior a aquella data.
# S'executa despres de la cadena setmanal (pas previ del workflow normalitzador_v3.yml) i
# es pot repetir sense risc: si els preus no han canviat, no afegeix res.

import json
import os
from collections import Counter
from datetime import date

from normalitzador_v3 import a_float

PESTANYA = 'Historic_Preus'
CAPCALERA = ['data', 'supermercat', 'producte', 'preu']
MIDA_BLOC = 5000


def obrir_historic(sheet):
    import gspread
    try:
        return sheet.worksheet(PESTANYA)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=PESTANYA, rows=1000, cols=len(CAPCALERA))
        ws.append_row(CAPCALERA)
        print(f"Pestanya '{PESTANYA}' creada")
        return ws


def main():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')

    # Preus actuals: un preu per supermercat + producte
    actuals = {}
    for f in sheet.worksheet('Preus').get_all_records():
        clau = (str(f.get('supermercat', '')).strip(), str(f.get('producte', '')).strip())
        preu = round(a_float(f.get('preu')), 2)
        if clau[1] and preu > 0 and clau not in actuals:
            actuals[clau] = (preu, str(f.get('data', '') or '')[:10] or str(date.today()))

    # Ultim preu conegut de cada producte (les files s'afegeixen en ordre de data)
    ws = obrir_historic(sheet)
    ultim = {}
    for fila in ws.get_all_values()[1:]:
        if len(fila) >= 4:
            ultim[(fila[1], fila[2])] = round(a_float(fila[3]), 2)

    noves, tipus = [], Counter()
    for (supermercat, producte), (preu, data) in actuals.items():
        anterior = ultim.get((supermercat, producte))
        if anterior == preu:
            tipus['sense canvi'] += 1
            continue
        tipus['nou' if anterior is None else ('puja' if preu > anterior else 'baixa')] += 1
        noves.append([data, supermercat, producte, preu])

    for i in range(0, len(noves), MIDA_BLOC):
        ws.append_rows(noves[i:i + MIDA_BLOC], value_input_option='RAW')

    print(f"Preus: {len(actuals)} productes | historic abans: {len(ultim)} productes")
    print(f"Files afegides a {PESTANYA}: {len(noves)} "
          f"(nous {tipus['nou']}, pugen {tipus['puja']}, baixen {tipus['baixa']}; "
          f"sense canvi {tipus['sense canvi']})")
    per_super = Counter(f[1] for f in noves if (f[1], f[2]) in ultim)
    if per_super:
        print(f"Canvis de preu per supermercat: {dict(per_super)}")
    celles = sum(w.row_count * w.col_count for w in sheet.worksheets())
    print(f"Cel·les del Google Sheet: {celles:,} de 10.000.000 ({celles / 100000:.1f}%)")


if __name__ == '__main__':
    main()
