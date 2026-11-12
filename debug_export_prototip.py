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

from normalitzador_v3 import (MarquesBlanques, comparar, llegir_atributs, llegir_preus, preu_unitat,
                              quantitat_comparable, referencies_preu, sense_accents)


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
    # 10/11: preu per kg/l amb la mateixa regla que normalitzador_v3.comparar (quantitat de la web)
    referencies = referencies_preu(preus, atributs)

    # Grups de comparacio: la mateixa clau que normalitzador_v3.comparar
    grups, index_grup, productes = [], {}, []
    for f in preus:
        a = atributs.get((f['supermercat'], f['producte']))
        pu, u = (None, '')
        if a and a['producte']:
            pu, u = preu_unitat(f['preu'], *quantitat_comparable(
                f['producte'], f['quantitat'], a, f['preu'], referencies.get((a['categoria'], a['unitat'])))[:3])
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

    # Comprovacio: el millor preu i el supermercat mes barat de cada grup (el que mostra el prototip)
    # han de coincidir amb Comparacions_v3 del full
    millors = {}
    for p in productes:
        if p[7] >= 0 and p[6]:
            g = millors.setdefault(p[7], {})
            if p[0] not in g or p[6] < g[p[0]]:
                g[p[0]] = p[6]
    del_prototip = Counter((round(min(g.values()), 2), min(g, key=g.get)) for g in millors.values() if len(g) > 1)
    full = sheet.worksheet('Comparacions_v3').get_all_values()[1:]
    del_full = Counter((round(float(str(f[11]).replace(',', '.')), 2), f[12]) for f in full if f[11])
    del_codi = Counter((round(f[11], 2), f[12]) for f in comparar(preus, atributs, marques))
    print(f"\nComprovacio: grups comparables al prototip {sum(del_prototip.values())} | files de Comparacions_v3 "
          f"{sum(del_full.values())} | comparar() ara {sum(del_codi.values())}")
    print(f"   prototip = full (millor preu i supermercat): {sum((del_prototip & del_full).values())} | "
          f"nomes al prototip: {sum((del_prototip - del_full).values())} | nomes al full: {sum((del_full - del_prototip).values())}")
    print(f"   full = comparar() d'ara: {sum((del_full & del_codi).values())} de {sum(del_full.values())}")
    for k, n in list((del_prototip - del_full).items())[:10]:
        print('   nomes prototip:', k, n)
    for k, n in list((del_full - del_prototip).items())[:10]:
        print('   nomes full:', k, n)

if __name__ == '__main__':
    main()
