# debug_cerca.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu enlloc, sense
# Gemini). Busca productes a Preus pel nom i mostra preu, format, preu per kg/l (mateixa regla que
# normalitzador_v3) i la comparacio on surten. Canviar CERCA per buscar una altra cosa.
import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3

CERCA = ['oetker', 'ristorante', 'casa di mama', 'la mia grande', 'tradizionale', 'flammkuchen']


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = nv3.llegir_preus(sheet)
    atributs = nv3.llegir_atributs(sheet.worksheet('Productes_Atributs'))
    ref = nv3.referencies_preu(preus, atributs)
    trobats = [f for f in preus if any(c in f['producte'].lower() for c in CERCA)]
    print(f"Cerca {CERCA}: {len(trobats)} productes")
    for f in sorted(trobats, key=lambda f: (nv3.SUPERMERCATS.index(f['supermercat']) if f['supermercat'] in nv3.SUPERMERCATS else 9, f['producte'])):
        a = atributs.get((f['supermercat'], f['producte']))
        pu, ue, attr = None, '', ''
        if a and a['producte']:
            u, m, un, motiu = nv3.quantitat_comparable(f['producte'], f['quantitat'], a, f['preu'], ref.get((a['categoria'], a['unitat'])))
            pu, ue = nv3.preu_unitat(f['preu'], u, m, un)
            attr = f"{a['marca']} / {a['producte']} / {a['variant'] or 'normal'}"
        print(f"   {f['supermercat'][:10]:<10} | {f['producte'][:70]:<70} | {f['preu']:>6.2f} € | {f['quantitat']!s:>10} | "
              f"{(round(pu, 2) if pu else '-')!s:>6} {ue:<5} | {attr}")


if __name__ == '__main__':
    main()
