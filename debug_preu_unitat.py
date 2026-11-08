# debug_preu_unitat.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu
# enlloc) i no crida Gemini (cost 0 €).
#
# Problema (INCIDENCIES item 26): el preu per kg/l de les comparacions fa servir la quantitat
# que va decidir Gemini, guardada a Productes_Atributs per nom. Errors x10, kg sense passar a g,
# caché obsoleta si el format canvia, dos formats amb el mateix nom...
# Regla nova que es prova: quantitat de la web de cada setmana (columna quantitat de Preus); la de
# Gemini nomes si la web no en te, si les unitats no lliguen (g/ml/u) o si coincideix amb un pack
# que diu el nom ("pack 24 latas 33 cl", "2x210 g") i la web nomes dona la mida d'una unitat.
# Compara les comparacions actuals amb les que sortirien amb la regla nova.
# 08/11 (2a versio): la regla ja es a normalitzador_v3.quantitat_comparable; aqui es reconstrueix
# la comparacio antiga per comparar-les.

import inspect
import json
import os
import random
from collections import Counter, defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3
from normalitzador_v3 import MarquesBlanques, comparar, llegir_atributs, llegir_preus

quantitat_final = nv3.quantitat_comparable


def comparar_antic():
    # normalitzador_v3.comparar tal com era abans del 08/11: quantitat de Gemini (cache)
    font = inspect.getsource(comparar)
    nou = ("pu, u = preu_unitat(f['preu'], *quantitat_comparable(\n            f['producte'], f['quantitat'], a, "
           "f['preu'], referencies.get((a['categoria'], a['unitat'])))[:3])")
    assert font.count(nou) == 1
    font = font.replace(nou, "pu, u = preu_unitat(f['preu'], a['unitats'], a['mida'], a['unitat'])")
    espai = dict(vars(nv3))
    exec(font, espai)
    return espai['comparar']


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = llegir_preus(sheet)
    atributs = llegir_atributs(sheet.worksheet('Productes_Atributs'))
    marques = MarquesBlanques(sheet.worksheet('Marques_Blanques').get_all_records(), atributs)
    print(f"Preus: {len(preus)} | atributs: {len(atributs)}")
    ref = nv3.referencies_preu(preus, atributs)
    refa = lambda f, a: (f['preu'], ref.get((a['categoria'], a['unitat'])))

    # 1. D'on surt la quantitat amb la regla nova
    motius, exemples = defaultdict(Counter), defaultdict(list)
    for f in preus:
        a = atributs.get((f['supermercat'], f['producte']))
        if not a or not a['producte']:
            continue
        unitats, mida, unitat, motiu = quantitat_final(f['producte'], f['quantitat'], a, *refa(f, a))
        motius[f['supermercat']][motiu] += 1
        if motiu.startswith('web') or motiu.endswith('nom') or 'escala' in motiu:
            exemples[motiu].append(f"{f['supermercat'][:10]:<10} | {f['quantitat']!r:>14} | gemini "
                                   f"{nv3.numero_net(a['unitats'])}x{nv3.numero_net(a['mida'])}{a['unitat']} -> "
                                   f"{nv3.numero_net(unitats)}x{nv3.numero_net(mida)}{unitat} | {f['preu']}€ | {f['producte'][:65]}")
    print("\nD'on surt la quantitat (regla nova):")
    for s, c in motius.items():
        t = sum(c.values())
        print(f"   {s} ({t}): " + ', '.join(f"{k} {v} ({100 * v / t:.1f}%)" for k, v in c.most_common()))
    random.seed(8)
    for motiu, llista in exemples.items():
        print(f"\nExemples a l'atzar ({motiu}, {len(llista)} en total):")
        for e in random.sample(llista, min(35, len(llista))):
            print('   ', e)

    # 2. Comparacions actuals vs regla nova
    vell = {tuple(f[:6]): f for f in comparar_antic()(preus, atributs, marques)}
    nou = {tuple(f[:6]): f for f in comparar(preus, atributs, marques)}
    comuns = vell.keys() & nou.keys()
    canvi_barat = [k for k in comuns if vell[k][12] != nou[k][12]]
    canvi_preu = [k for k in comuns if abs(nou[k][11] / vell[k][11] - 1) > 0.03] if comuns else []
    print(f"\nComparacions: ara {len(vell)} | regla nova {len(nou)} | comunes {len(comuns)} | "
          f"noves {len(nou.keys() - vell.keys())} | desapareixen {len(vell.keys() - nou.keys())}")
    print(f"   canvia el supermercat mes barat: {len(canvi_barat)} | canvia el millor preu per kg/l (>3%): {len(canvi_preu)}")
    print(f"   marcades 'Revisar' (x2,5): ara {sum(1 for f in vell.values() if f[16])} | "
          f"regla nova {sum(1 for f in nou.values() if f[16])}")
    print("\nExemples on canvia el mes barat (abans -> despres):")
    for k in sorted(canvi_barat, key=lambda k: -abs(nou[k][11] / vell[k][11] - 1))[:40]:
        v, n = vell[k], nou[k]
        print(f"   {k[2]} | {k[3]} {k[4]} {k[5]} | {v[12]} {v[11]} ({v[15][:40]}) -> {n[12]} {n[11]} ({n[15][:40]})")

    # 3. Casos coneguts de l'auditoria del 08/11
    print("\nCasos coneguts:")
    for text in ('Calabacín Simpl', 'Frambuesa 170', 'Mini bolas sabor queso', 'Nachos Hacendado',
                 'BONPREU Oli refinat de gira-sol', 'Coca Cola zero azúcar pack 24', 'La Gula del Norte 2x210',
                 'Café cápsulas Colombia Starbucks', 'Lombarda 1 Kg', 'Sopa juliana Trevijano', 'Pienso de salmón y trigo para gatos esterilizados Purina',
                 'Pepsi zero azúcar', 'Ekosan perfumador', 'Detergent Perlan', 'Insecticida cucarachas'):
        for f in preus:
            a = atributs.get((f['supermercat'], f['producte']))
            if a and text.lower() in f['producte'].lower():
                antic = nv3.preu_unitat(f['preu'], a['unitats'], a['mida'], a['unitat'])
                q = quantitat_final(f['producte'], f['quantitat'], a, *refa(f, a))
                nou_pu = nv3.preu_unitat(f['preu'], *q[:3])
                print(f"   {f['supermercat'][:10]:<10} | {f['producte'][:50]:<50} | {f['preu']}€ {f['quantitat']!r} | "
                      f"ara {antic[0] and round(antic[0], 2)}{antic[1]} -> {nou_pu[0] and round(nou_pu[0], 2)}{nou_pu[1]} ({q[3]})")


if __name__ == '__main__':
    main()
