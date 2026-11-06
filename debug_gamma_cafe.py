# debug_gamma_cafe.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu
# a Productes_Atributs ni enlloc). Crida Gemini nomes per a la categoria "cafe" (~0,30 €).
#
# Problema (INCIDENCIES item 24): el normalitzador v3 agrupa models diferents d'una marca.
# Lavazza "Qualità Oro" i "Crema e Gusto" queden tots dos com a "cafè mòlt natural" de Lavazza.
# Prova: el mateix prompt del v3 amb un camp nou, "gamma" (linia o model comercial), i
# comparacio dels grups abans i despres per a la categoria del cafe.

import json
import os
import time
from collections import Counter, defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from normalitzador_v3 import (PROMPT_ATRIBUTS, SUPERMERCATS, ClientGemini, MarquesBlanques,
                              a_float, construir_vocabularis, llegir_atributs, llegir_preus,
                              numero_net, preu_unitat, sense_accents, text_variant,
                              vocabulari_per_prompt)

CATEGORIA = 'cafe'
MIDA_LOT = 80

PROMPT_GAMMA = PROMPT_ATRIBUTS.replace(
    "- producte: què és,",
    "- gamma: per a les marques de fabricant, el nom de la línia o model comercial que\n"
    "  distingeix productes de la mateixa marca i producte (\"Qualità Oro\", \"Crema e Gusto\",\n"
    "  \"Espresso Barista\", \"Gran Selección\"...), escrit sempre igual i sense la marca. Fes\n"
    "  servir les gammes del vocabulari si n'hi ha una d'equivalent. \"\" si no en té, si és\n"
    "  marca blanca o si el nom només diu trets que ja van a variant.\n"
    "- producte: què és,"
).replace(
    "{\"r\": [[id, marca, producte, [variants], marca_blanca, unitats, mida, unitat], ...]}",
    "{\"r\": [[id, marca, gamma, producte, [variants], marca_blanca, unitats, mida, unitat], ...]}"
)


def main():
    assert PROMPT_GAMMA != PROMPT_ATRIBUTS and '"gamma"' not in PROMPT_ATRIBUTS
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = llegir_preus(sheet)
    atributs = llegir_atributs(sheet.worksheet('Productes_Atributs'))
    marques = MarquesBlanques(sheet.worksheet('Marques_Blanques').get_all_records(), atributs)
    vocabulari = vocabulari_per_prompt(construir_vocabularis(
        {k: a for k, a in atributs.items() if a['categoria'] == CATEGORIA})[CATEGORIA])

    cafe = []
    for p in preus:
        a = atributs.get((p['supermercat'], p['producte']))
        if a and a['categoria'] == CATEGORIA:
            cafe.append(dict(p, id=f"P{len(cafe)}", antic=a))
    print(f"Productes de cafe: {len(cafe)}")

    gemini = ClientGemini(os.environ['GEMINI_API_KEY'])
    gammes = defaultdict(Counter)   # marca -> gammes ja fetes servir (vocabulari compartit entre lots)
    nous = {}
    inici = time.time()
    for i in range(0, len(cafe), MIDA_LOT):
        lot = cafe[i:i + MIDA_LOT]
        voc = dict(vocabulari, gammes={m: [g for g, _ in c.most_common(15)] for m, c in gammes.items()})
        dades = {'vocabulari': voc,
                 'productes': [{'id': p['id'], 's': p['supermercat'], 'n': p['producte'], 'q': p['quantitat']}
                               for p in lot]}
        for f in gemini.cridar(PROMPT_GAMMA, dades):
            if not (isinstance(f, list) and len(f) >= 9):
                continue
            _, marca, gamma, producte, variants, mb, unitats, mida, unitat = f[:9]
            unitat = str(unitat or '').strip().lower()
            nous[str(f[0])] = {
                'marca': str(marca or '').strip(), 'gamma': str(gamma or '').strip(),
                'producte': str(producte or '').strip().lower(),
                'variant': text_variant(variants if isinstance(variants, list) else [variants]),
                'marca_blanca': 1 if str(mb).strip() in ('1', 'True', 'true') else 0,
                'unitats': numero_net(a_float(unitats) or 1), 'mida': numero_net(a_float(mida)),
                'unitat': unitat if unitat in ('ml', 'g', 'u') else ''}
            if nous[str(f[0])]['gamma']:
                gammes[nous[str(f[0])]['marca']][nous[str(f[0])]['gamma']] += 1
        print(f"   lot {i // MIDA_LOT + 1}: {len(nous)}/{min(i + MIDA_LOT, len(cafe))} | tokens sortida {gemini.tokens_sortida}")

    def grups(clau_attr):
        g = defaultdict(set)
        for p in cafe:
            a = clau_attr(p)
            if not a or not a['producte']:
                continue
            pu, u = preu_unitat(p['preu'], a['unitats'], a['mida'], a['unitat'])
            if not pu or marques.es_blanca(a['marca'], p['supermercat'], a['marca_blanca']):
                continue
            g[(sense_accents(a['marca']), sense_accents(a.get('gamma', '')), sense_accents(a['producte']),
               sense_accents(a['variant']), u)].add(p['supermercat'])
        return g

    abans = grups(lambda p: p['antic'])
    despres = grups(lambda p: nous.get(p['id']))
    print(f"\nMarca comercial, grups: abans {len(abans)} (comparables {sum(1 for s in abans.values() if len(s) > 1)}) | "
          f"despres {len(despres)} (comparables {sum(1 for s in despres.values() if len(s) > 1)})")
    print(f"Productes amb gamma: {sum(1 for a in nous.values() if a['gamma'])}/{len(nous)}")
    print("\nGammes per marca (les 25 marques amb mes productes):")
    for m, c in sorted(gammes.items(), key=lambda kv: -sum(kv[1].values()))[:25]:
        print(f"   {m}: {dict(c.most_common(12))}")
    print("\nExemples (Lavazza, Marcilla, Nespresso/compatibles, Bonka, Saimaza):")
    for p in cafe:
        a = nous.get(p['id'])
        if a and any(k in p['producte'].lower() for k in ('lavazza', 'marcilla', 'bonka', 'saimaza', 'starbucks', "l'or")):
            print(f"   {p['supermercat'][:10]:<10} | {p['producte'][:55]:<55} | gamma={a['gamma']!r} "
                  f"producte={a['producte']!r} variant={a['variant']!r} | abans variant={p['antic']['variant']!r}")
    print(f"\nTokens Gemini: entrada={gemini.tokens_entrada} sortida={gemini.tokens_sortida} | "
          f"{(time.time() - inici) / 60:.1f} min")


if __name__ == '__main__':
    main()
