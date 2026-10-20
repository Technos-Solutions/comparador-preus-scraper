# historic_preus.py — Historic de preus (des del 19/10/2026)
#
# Es desa en un Google Sheet a part, "Comparador_Preus_Historic" (pestanya Historic_Preus),
# perque es l'unica dada que creix cada setmana i el full principal ja es al ~55% del limit
# de 10 milions de cel·les. Llegeix els preus actuals de la pestanya Preus del full principal.
#
# Per no omplir el Google Sheet (limit de 10 milions de cel·les) nomes es desa una fila
# quan un producte apareix per primer cop o quan li canvia el preu o el format:
#   data | supermercat | producte | preu | quantitat | envas
# El format (quantitat + envas) permet calcular el preu per kg/l de cada data i detectar
# la "reduflacio" (mateix preu, menys producte). El preu d'un producte en una data
# qualsevol es el de l'ultima fila anterior a aquella data.
# S'executa despres de la cadena setmanal (pas previ del workflow normalitzador_v3.yml) i
# es pot repetir sense risc: si res no ha canviat, no afegeix res.
# REINICIAR=1 buida la pestanya abans d'escriure (nomes per canvis d'estructura).

import json
import os
from collections import Counter
from datetime import date

from normalitzador_v3 import a_float

FULL_PRINCIPAL = 'Comparador_Preus_DB'
FULL_HISTORIC = 'Comparador_Preus_Historic'   # creat pel David i compartit amb el compte de servei
PESTANYA = 'Historic_Preus'
CAPCALERA = ['data', 'supermercat', 'producte', 'preu', 'quantitat', 'envas']
MIDA_BLOC = 5000


def text_quantitat(valor):
    # "1.5", "1,5" i 1.5 son la mateixa quantitat; el que no es numeric es deixa tal qual
    text = str(valor if valor is not None else '').strip()
    numero = a_float(text)
    if numero or text in ('0', '0.0'):
        return str(int(numero)) if float(numero).is_integer() else str(round(numero, 3))
    return text


def obrir_historic(sheet):
    import gspread
    try:
        ws = sheet.worksheet(PESTANYA)
        if ws.col_count < len(CAPCALERA):
            ws.add_cols(len(CAPCALERA) - ws.col_count)
        return ws
    except gspread.WorksheetNotFound:
        pestanyes = sheet.worksheets()
        if len(pestanyes) == 1 and not pestanyes[0].get_all_values():
            # Full nou: es reaprofita la pestanya buida que porta per defecte ("Full 1")
            ws = pestanyes[0]
            ws.update_title(PESTANYA)
            ws.resize(rows=1000, cols=len(CAPCALERA))
        else:
            ws = sheet.add_worksheet(title=PESTANYA, rows=1000, cols=len(CAPCALERA))
        ws.append_row(CAPCALERA)
        print(f"Pestanya '{PESTANYA}' creada a {FULL_HISTORIC}")
        return ws


def main():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    client = gspread.authorize(creds)
    sheet = client.open(FULL_PRINCIPAL)
    sheet_historic = client.open(FULL_HISTORIC)

    # Preus actuals: preu i format per supermercat + producte
    actuals = {}
    for f in sheet.worksheet('Preus').get_all_records():
        clau = (str(f.get('supermercat', '')).strip(), str(f.get('producte', '')).strip())
        preu = round(a_float(f.get('preu')), 2)
        if clau[1] and preu > 0 and clau not in actuals:
            format_ = (text_quantitat(f.get('quantitat')), str(f.get('envas', '') or '').strip())
            actuals[clau] = (preu, format_, str(f.get('data', '') or '')[:10] or str(date.today()))

    ws = obrir_historic(sheet_historic)
    if os.environ.get('REINICIAR') == '1':
        ws.clear()
        ws.append_row(CAPCALERA)
        print(f"{PESTANYA} buidada (REINICIAR=1)")
    # Valors sense format: el full de l'historic es en catala (ca_ES, "17,25") i el principal en
    # angles (en_US, "17.25"); amb els valors purs no depenem del format de cada full
    files = ws.get_all_values(value_render_option='UNFORMATTED_VALUE')
    files = [[str(x) for x in fila] for fila in files]
    if files and files[0] != CAPCALERA:
        raise SystemExit(f"La capcalera de {PESTANYA} no es {CAPCALERA}: no es barregen estructures")

    # Ultim preu i format coneguts de cada producte (les files s'afegeixen en ordre de data)
    ultim = {}
    for fila in files[1:]:
        if len(fila) >= 6:
            ultim[(fila[1], fila[2])] = (round(a_float(fila[3]), 2), (text_quantitat(fila[4]), fila[5].strip()))

    noves, tipus = [], Counter()
    for (supermercat, producte), (preu, format_, data) in actuals.items():
        anterior = ultim.get((supermercat, producte))
        if anterior == (preu, format_):
            tipus['sense canvi'] += 1
            continue
        if anterior is None:
            tipus['nou'] += 1
        elif anterior[1] != format_:
            tipus['canvi de format'] += 1
        else:
            tipus['puja' if preu > anterior[0] else 'baixa'] += 1
        quantitat = a_float(format_[0]) if text_quantitat(a_float(format_[0])) == format_[0] else format_[0]
        noves.append([data, supermercat, producte, preu, quantitat, format_[1]])

    for i in range(0, len(noves), MIDA_BLOC):
        ws.append_rows(noves[i:i + MIDA_BLOC], value_input_option='RAW')

    print(f"Preus: {len(actuals)} productes | historic abans: {len(ultim)} productes")
    print(f"Files afegides a {PESTANYA}: {len(noves)} "
          f"(nous {tipus['nou']}, pugen {tipus['puja']}, baixen {tipus['baixa']}, "
          f"canvi de format {tipus['canvi de format']}; sense canvi {tipus['sense canvi']})")
    per_super = Counter(f[1] for f in noves if (f[1], f[2]) in ultim)
    if per_super:
        print(f"Canvis (preu o format) per supermercat: {dict(per_super)}")
    for nom, full in ((FULL_PRINCIPAL, sheet), (FULL_HISTORIC, sheet_historic)):
        celles = sum(w.row_count * w.col_count for w in full.worksheets())
        print(f"Cel·les de {nom}: {celles:,} de 10.000.000 ({celles / 100000:.1f}%)")


if __name__ == '__main__':
    main()
