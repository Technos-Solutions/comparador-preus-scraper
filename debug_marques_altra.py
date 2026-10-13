# debug_marques_altra.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets,
# no crida Gemini ni escriu res.
#
# Run del normalitzador v3 del 13/10 (veure INCIDENCIES.md):
#   1. Ha afegit 35 marques blanques "pendent" que son marques de licor (Baileys, Smirnoff,
#      Johnnie Walker...). Es mira, per a cada marca pendent, a quants supermercats es ven:
#      una marca blanca nomes es ven al seu supermercat, aixi que si surt a 2 o mes no ho es.
#   2. Els lots 5 a 19 de la categoria "altra" van gastar exactament 2.085 tokens de sortida
#      cadascun: es comprova si Gemini va tornar files buides (sense producte ni format).

import json
import os
from collections import Counter, defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from normalitzador_v3 import MarquesBlanques, sense_accents


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    atributs = sheet.worksheet('Productes_Atributs').get_all_records()
    files_marques = sheet.worksheet('Marques_Blanques').get_all_records()
    print(f"Productes_Atributs: {len(atributs)} files | Marques_Blanques: {len(files_marques)} files")

    print("\n######## 1. Marques blanques: a quants supermercats es ven cada marca ########")
    supers_marca = defaultdict(set)
    productes_marca = Counter()
    for a in atributs:
        m = sense_accents(a.get('marca'))
        if m:
            supers_marca[m].add(str(a.get('supermercat', '')).strip())
            productes_marca[m] += 1
    per_estat = defaultdict(list)
    for f in files_marques:
        per_estat[str(f.get('estat', '')).strip().lower()].append(f)
    print(f"Estats: { {e: len(ll) for e, ll in per_estat.items()} }")
    for estat in ('pendent', 'confirmada'):
        multi = []
        for f in per_estat.get(estat, []):
            m = sense_accents(f.get('marca'))
            supers = supers_marca.get(m, set())
            if len(supers) >= 2:
                multi.append((f.get('marca'), f.get('supermercat'), f.get('data'), sorted(supers),
                              productes_marca[m]))
        print(f"\n{estat}: {len(per_estat.get(estat, []))} | es venen a 2 o mes supermercats: {len(multi)}")
        for marca, s, data, supers, n in multi:
            print(f"   {marca!r:<28} ({s}, {data}) -> {n} productes a {supers}")
    print("\nPendents que nomes surten a 1 supermercat (candidates de veritat):")
    for f in per_estat.get('pendent', []):
        m = sense_accents(f.get('marca'))
        if len(supers_marca.get(m, set())) < 2:
            print(f"   {f.get('supermercat')}: {f.get('marca')} ({productes_marca[m]} productes, {f.get('data')})")

    # Quants productes canvien de grup a la comparacio si s'aplica la regla dels 2 supermercats
    marques = MarquesBlanques(files_marques)
    canvien = Counter()
    for a in atributs:
        m = sense_accents(a.get('marca'))
        s = str(a.get('supermercat', '')).strip()
        mb = str(a.get('marca_blanca', '')).strip() in ('1', '1.0')
        if m and len(supers_marca.get(m, set())) >= 2 and marques._estat(a.get('marca'), s) != 'confirmada' \
                and marques.es_blanca(a.get('marca'), s, mb):
            canvien[(s, a.get('marca'))] += 1
    print(f"\nProductes que ara compten com a marca blanca i es venen a 2+ supermercats: "
          f"{sum(canvien.values())}")
    for (s, m), n in canvien.most_common(40):
        print(f"   {s}: {m} ({n})")

    print("\n######## 2. Categoria 'altra' del 13/10 ########")
    altra = [a for a in atributs if a.get('categoria') == 'altra']
    avui = [a for a in altra if str(a.get('data')) == '2026-10-13']
    buides = [a for a in avui if not str(a.get('producte', '')).strip()]
    sense_mida = [a for a in avui if not str(a.get('mida', '')).strip() or str(a.get('mida')) in ('0', '0.0')]
    print(f"altra: {len(altra)} | del 13/10: {len(avui)} | sense producte: {len(buides)} | sense mida: {len(sense_mida)}")
    print(f"Per supermercat (13/10): {dict(Counter(a.get('supermercat') for a in avui))}")
    print(f"Productes mes repetits (13/10): {Counter(a.get('producte') for a in avui).most_common(15)}")
    # Mostra seguida de files desades (en l'ordre del full = ordre dels lots)
    print("\nMostra de files del 13/10 (cada 80, ~1 per lot):")
    for a in avui[::80][:30]:
        print(f"   {a.get('supermercat'):<18} | {str(a.get('nom_original'))[:45]:<45} -> "
              f"marca={a.get('marca')!r} producte={a.get('producte')!r} variant={a.get('variant')!r} "
              f"mb={a.get('marca_blanca')} {a.get('unitats')}x{a.get('mida')}{a.get('unitat')}")
    print("\n20 files seguides del mig (lots 5-19):")
    for a in avui[600:620]:
        print(f"   {a.get('supermercat'):<18} | {str(a.get('nom_original'))[:45]:<45} -> "
              f"{a.get('marca')!r} | {a.get('producte')!r} | {a.get('variant')!r} | "
              f"{a.get('unitats')}x{a.get('mida')}{a.get('unitat')}")


if __name__ == '__main__':
    main()
