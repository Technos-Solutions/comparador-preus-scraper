# debug_export_prototip.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets.
# Exporta al registre les dades reals per al prototip visual de l'aplicacio, comprimides
# (gzip + base64) perque el registre no sigui massa gran:
#   - tots els productes de Preus amb els seus atributs (Productes_Atributs), el preu per
#     unitat i el grup de comparacio, amb la mateixa logica que normalitzador_v3.comparar
#   - els canvis de l'historic de preus (ultima fila i anterior de cada producte)
#   - les marques blanques confirmades
# No escriu res i no crida Gemini.

import base64
import gzip
import json
import os
from collections import Counter

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from normalitzador_v3 import (MarquesBlanques, llegir_atributs, llegir_preus, preu_unitat,
                              sense_accents)


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    client = gspread.authorize(creds)
    sheet = client.open('Comparador_Preus_DB')
    preus = llegir_preus(sheet)
    atributs = llegir_atributs(sheet.worksheet('Productes_Atributs'))
    files_marques = sheet.worksheet('Marques_Blanques').get_all_records()
    marques = MarquesBlanques(files_marques, atributs)

    # Grups de comparacio: la mateixa clau que normalitzador_v3.comparar
    grups, index_grup, productes = [], {}, []
    for f in preus:
        a = atributs.get((f['supermercat'], f['producte']))
        pu, u = (None, '')
        if a and a['producte']:
            pu, u = preu_unitat(f['preu'], a['unitats'], a['mida'], a['unitat'])
        gid = -1
        mb = 0
        if a and a['producte'] and pu:
            mb = 1 if marques.es_blanca(a['marca'], f['supermercat'], a['marca_blanca']) else 0
            producte, variant = sense_accents(a['producte']), sense_accents(a['variant'])
            clau = ((a['categoria'], producte, variant, u) if mb else
                    (a['categoria'], sense_accents(a['marca']), producte, variant, u))
            if clau not in index_grup:
                index_grup[clau] = len(grups)
                grups.append([mb, a['categoria'], a['marca'], a['producte'], a['variant'], u])
            gid = index_grup[clau]
        productes.append([f['supermercat'], f['producte'], round(f['preu'], 2), f['quantitat'],
                          (a or {}).get('categoria', ''), (a or {}).get('marca', ''),
                          round(pu, 3) if pu else None, gid, mb])

    historic = client.open('Comparador_Preus_Historic').worksheet('Historic_Preus') \
        .get_all_values(value_render_option='UNFORMATTED_VALUE')
    per_producte = {}
    for fila in historic[1:]:
        per_producte.setdefault((fila[1], fila[2]), []).append(fila)
    canvis = [[f[-2], f[-1]] for f in per_producte.values() if len(f) >= 2]
    confirmades = [[f['marca'], f['supermercat']] for f in files_marques
                   if str(f.get('estat', '')).strip().lower() == 'confirmada']

    dades = {'grups': grups, 'productes': productes, 'canvis': canvis, 'marques': confirmades}
    comprimit = base64.b64encode(gzip.compress(json.dumps(dades, ensure_ascii=False,
                                                          separators=(',', ':')).encode())).decode()
    print('###INICI_B64###')
    for i in range(0, len(comprimit), 20000):
        print(comprimit[i:i + 20000])
    print('###FI_B64###')
    print(f"Productes: {len(productes)} | grups: {len(grups)} | canvis: {len(canvis)} | "
          f"base64: {len(comprimit)} caracters")
    mida_grup = Counter(p[7] for p in productes if p[7] >= 0)
    print(f"Grups amb 2+ productes: {sum(1 for n in mida_grup.values() if n >= 2)}")

    # Diagnostic: per que "Lavazza Oro" no surt a les comparacions
    print('\n--- Lavazza ---')
    for p in productes:
        if 'lavazza' in p[1].lower():
            a = atributs.get((p[0], p[1]), {})
            print(f"{p[0]:<18} | {p[1][:60]:<60} | {p[2]} | {p[3]} | marca={a.get('marca')!r} "
                  f"producte={a.get('producte')!r} variant={a.get('variant')!r} "
                  f"{a.get('unitats')}x{a.get('mida')}{a.get('unitat')} | grup {p[7]}")


if __name__ == '__main__':
    main()
