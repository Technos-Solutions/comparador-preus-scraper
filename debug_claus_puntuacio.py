# debug_claus_puntuacio.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu
# enlloc) i no crida Gemini.
#
# Problema (12/11, pizzes Dr. Oetker): Gemini escriu la mateixa marca de dues maneres ("Dr Oetker" i
# "Dr. Oetker") i normalitzador_v3 compara amb sense_accents(), que treu accents i majuscules pero
# no la puntuacio: queden com a marques diferents i el mateix producte no es compara.
# Prova: claus sense puntuacio ("dr. oetker" -> "dr oetker", "l'or" -> "l or")
#   A) nomes a la marca de les comparacions
#   B) a totes les claus (marca, producte, variant i el recompte de marques de Marques_Blanques)
import inspect
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3

ORIGINAL = nv3.sense_accents


def sense_puntuacio(text):
    text = unicodedata.normalize('NFKD', str(text or '')).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.lower().replace('-', ' ')).split())


def comparar_nomes_marca():
    font = inspect.getsource(nv3.comparar)
    vell = "comercials[(a['categoria'], sense_accents(a['marca']), producte, variant, u)]"
    assert font.count(vell) == 1
    font = font.replace(vell, "comercials[(a['categoria'], sense_puntuacio(a['marca']), producte, variant, u)]")
    espai = dict(vars(nv3), sense_puntuacio=sense_puntuacio)
    exec(font, espai)
    return espai['comparar']


def resum(nom, files):
    tipus = Counter(f[0] for f in files)
    print(f"   {nom}: {len(files)} comparacions {dict(tipus)} | Revisar: {sum(1 for f in files if f[-2])}")


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = nv3.llegir_preus(sheet)
    atributs = nv3.llegir_atributs(sheet.worksheet('Productes_Atributs'))
    files_marques = sheet.worksheet('Marques_Blanques').get_all_records()

    ara = nv3.comparar(preus, atributs, nv3.MarquesBlanques(files_marques, atributs))
    a = comparar_nomes_marca()(preus, atributs, nv3.MarquesBlanques(files_marques, atributs))
    nv3.sense_accents = sense_puntuacio
    try:
        marques_b = nv3.MarquesBlanques(files_marques, atributs)
        b = nv3.comparar(preus, atributs, marques_b)
    finally:
        nv3.sense_accents = ORIGINAL
    print("Comparacions:")
    resum('ara', ara)
    resum('A (marca sense puntuacio)', a)
    resum('B (totes les claus sense puntuacio)', b)

    # Marques que s'ajunten: formes diferents que donen la mateixa clau nova
    formes = defaultdict(Counter)
    for at in atributs.values():
        if at['marca']:
            formes[sense_puntuacio(at['marca'])][ORIGINAL(at['marca'])] += 1
    unides = {k: c for k, c in formes.items() if len(c) > 1}
    print(f"\nMarques amb mes d'una forma que s'ajunten: {len(unides)}")
    for k, c in sorted(unides.items(), key=lambda kv: -sum(kv[1].values()))[:40]:
        print(f"   {k!r}: {dict(c.most_common(5))}")

    # Productes i variants que s'ajunten amb B
    for camp in ('producte', 'variant'):
        formes = defaultdict(Counter)
        for at in atributs.values():
            if at[camp]:
                formes[sense_puntuacio(at[camp])][ORIGINAL(at[camp])] += 1
        unides = {k: c for k, c in formes.items() if len(c) > 1}
        print(f"\n{camp}: formes que s'ajunten amb B: {len(unides)}")
        for k, c in sorted(unides.items(), key=lambda kv: -sum(kv[1].values()))[:15]:
            print(f"   {k!r}: {dict(c.most_common(4))}")

    # Comparacions noves amb B (claus que abans no hi eren), mes exemples Dr. Oetker
    claus_ara = {tuple(sense_puntuacio(x) for x in f[:6]) for f in ara}
    noves = [f for f in b if tuple(sense_puntuacio(x) for x in f[:6]) not in claus_ara]
    print(f"\nComparacions noves amb B: {len(noves)}. Exemples:")
    for f in noves[:30]:
        sups = [s for s, v in zip(nv3.SUPERMERCATS, f[6:11]) if v != '']
        print(f"   {f[0][:8]} | {f[2]} | {f[3]} {f[4]} {f[5]} | {', '.join(s[:9] for s in sups)} | barat {f[12]} {f[11]}")
    # C: B + sense la categoria a la clau de les marques comercials (Gemini posa el mateix producte
    # en categories diferents segons el supermercat: pizzes de Dia vs Bon Preu/Carrefour)
    font = inspect.getsource(nv3.comparar)
    vell = "comercials[(a['categoria'], sense_accents(a['marca']), producte, variant, u)]"
    assert font.count(vell) == 1
    font = font.replace(vell, "comercials[('', sense_accents(a['marca']), producte, variant, u)]")
    espai = dict(vars(nv3), sense_accents=sense_puntuacio)
    exec(font, espai)
    nv3.sense_accents = sense_puntuacio
    try:
        c = espai['comparar'](preus, atributs, nv3.MarquesBlanques(files_marques, atributs))
    finally:
        nv3.sense_accents = ORIGINAL
    resum('C (B + sense categoria a les marques comercials)', c)
    claus_b = {tuple(sense_puntuacio(x) for x in f[2:6]) for f in b if f[0] == 'Marca comercial'}
    noves_c = [f for f in c if f[0] == 'Marca comercial' and tuple(sense_puntuacio(x) for x in f[2:6]) not in claus_b]
    print(f"   comparacions comercials noves amb C: {len(noves_c)}. Exemples:")
    for f in noves_c[:25]:
        preus_s = ' | '.join(f"{s[:9]} {v}" for s, v in zip(nv3.SUPERMERCATS, f[6:11]) if v != '')
        print(f"   {f[2]} | {f[3]} {f[4]} {f[5]} | {preus_s} | Revisar {f[-2] or '-'}")
    print("\nCategoria de les pizzes Dr. Oetker per supermercat:")
    cats = Counter()
    for (sup, nom), at in atributs.items():
        if 'oetker' in at['marca'].lower() and at['producte'].lower() == 'pizza':
            cats[(sup, at['categoria'])] += 1
    for (sup, cat), n in sorted(cats.items()):
        print(f"   {sup}: {cat} ({n})")
    print("\nDr. Oetker amb C:")
    for f in c:
        if 'oetker' in str(f[2]).lower():
            preus_s = ' | '.join(f"{s[:9]} {v}" for s, v in zip(nv3.SUPERMERCATS, f[6:11]) if v != '')
            print(f"   {f[3]} {f[4]} {f[5]} | {preus_s}")
    print("\nDr. Oetker amb B:")
    for f in b:
        if 'oetker' in str(f[2]).lower():
            preus_s = ' | '.join(f"{s[:9]} {v}" for s, v in zip(nv3.SUPERMERCATS, f[6:11]) if v != '')
            print(f"   {f[3]} {f[4]} {f[5]} | {preus_s}")


if __name__ == '__main__':
    main()
