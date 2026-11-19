# debug_cerca.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu enlloc, sense
# Gemini). Busca productes a Preus pel nom i mostra preu, format, preu per kg/l (mateixa regla que
# normalitzador_v3) i la comparacio on surten. Canviar CERCA per buscar una altra cosa.
import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3

CERCA = ['nivea cellular sèrum facial', 'lindt xocolata blanca', 'freixenet meritum', 'alpro pack 6u', 'cesar menjar',
         'pepsi zero azúcar sabor lima 1,75', 'coca-cola refresc de cola zero sucre llima en ampolla', 'moritz cervesa']


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


def historic():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    files = gspread.authorize(creds).open('Comparador_Preus_Historic').worksheet('Historic_Preus') \
        .get_all_values(value_render_option='UNFORMATTED_VALUE')
    print(f"\nHistoric_Preus: {len(files) - 1} files. Historial dels productes cercats:")
    per = {}
    for f in files[1:]:
        if any(c in str(f[2]).lower() for c in CERCA):
            per.setdefault((f[1], f[2]), []).append(f)
    for (sup, nom), fs in sorted(per.items()):
        print(f"   {sup[:10]:<10} | {nom[:60]:<60} | " + ' -> '.join(f"{f[0]} {f[3]}€ {f[4]}" for f in fs))


if __name__ == '__main__':
    historic()
    main()
