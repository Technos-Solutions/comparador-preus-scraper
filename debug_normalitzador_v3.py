# debug_normalitzador_v3.py — Script de nomes diagnostic: LLEGEIX Preus i la
# cache del v2 de Google Sheets, pero NO hi escriu res.
#
# Prova el disseny del normalitzador v3 amb unes quantes categories senceres:
#   Pas A (categoria): es reaprofita la categoria de la cache del v2
#     (Productes_Normalitzats), que als diagnostics ha estat estable.
#     A produccio nomes caldria demanar-la per als productes nous.
#   Pas B (atributs amb vocabulari compartit): els productes de cada categoria
#     s'envien en lots barrejant supermercats. Cada lot rep el vocabulari dels
#     lots anteriors (noms de producte, variants i marques ja fets servir) i
#     ha de reutilitzar-lo si es el mateix producte. Aixi el nom no depen de
#     la crida, com una persona que treballa amb un cataleg.
#   Comparacio (codi, sense Gemini):
#     - Marques comercials: mateixa marca + producte + variant
#     - Marques blanques (llista fixa + Gemini + productes sense marca):
#       mateix producte + variant entre supermercats
#     - Nomes es comparen unitats iguals (€/l amb €/l)
#   Mesura: tokens i cost, quants grups comparables barregen lots diferents
#   (prova que el vocabulari funciona entre crides) i el vocabulari final.

import json
import os
import sys
import time
import unicodedata
from collections import defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types

MODEL = 'gemini-3.5-flash'
CATEGORIES = sys.argv[1:] or ['llet', 'oli', 'aigua']
MIDA_LOT = 80
MAX_PRODUCTES = 700          # limit dur per no gastar mes del saldo que queda
EUR_PER_M_SORTIDA = 8.0      # estimacio a partir del saldo gastat el 28/09 (entrada negligible)

SUPERMERCATS = ['Mercadona', 'Bon Àrea', 'Dia', 'Bon Preu / Esclat', 'Carrefour']

# Marques blanques (llista fixa ampliada amb les que va trobar Gemini l'01/10).
# Les que comencen igual que el supermercat (Dia Láctea, Carrefour Bio...) es
# detecten per prefix. Els productes sense marca compten com a marca blanca.
MARQUES_BLANQUES = {
    'Mercadona': ['hacendado', 'deliplus', 'bosque verde', 'compy', 'casa juncal'],
    'Dia': ['dia', 'vegecampo', 'delicious dia', 'bonte', 'la almazara del olivar',
            'el molino de dia'],
    'Carrefour': ['carrefour', 'el mercado', 'de nuestra tierra', 'simpl', 'sensation'],
    'Bon Preu / Esclat': ['bonpreu', 'bon preu', 'esclat', 'ifa', 'la collita'],
    'Bon Àrea': ['bonarea', 'bon area'],
}

PROMPT = """Ets una persona que compara preus entre supermercats (Mercadona, Bon Àrea,
Dia, Bon Preu/Esclat i Carrefour). Reps productes d'una mateixa categoria. Cada
supermercat escriu el nom a la seva manera (català o castellà).

Reps també un VOCABULARI amb els noms que ja s'han fet servir en aquesta categoria.
REGLA PRINCIPAL: si un producte és el mateix que un del vocabulari, fes servir
EXACTAMENT el mateix text de "producte", les mateixes variants i la mateixa marca.
Crea un nom nou només si no n'hi ha cap d'equivalent.

Per a cada producte, extreu:
- marca: marca comercial, sempre escrita igual (p. ex. "Coca-Cola", "Hacendado").
  Si no n'hi ha, "".
- producte: què és, en català, genèric i curt ("llet", "oli d'oliva", "aigua mineral").
- variant: llista de trets que el fan un producte DIFERENT (["sencera"],
  ["sencera", "sense lactosa"], ["verge extra"], ["amb gas"]...), en català i
  minúscules. [] si és la versió normal. Sense format, envàs ni quantitat.
- marca_blanca: 1 si és la marca pròpia del supermercat on es ven (Hacendado de
  Mercadona, Dia Láctea de Dia, Carrefour/El Mercado de Carrefour, Bonpreu/Ifa de
  Bon Preu, Bon Àrea...), 0 si no.
- unitats, mida, unitat: format del pack. unitat és "ml", "g" o "u". Converteix
  l i cl a ml, kg a g. Fes servir el nom i "q" (la quantitat de la web): si el nom
  no diu la mida, fes servir q; si q és la mida d'una sola unitat però el nom diu
  que és un pack ("pack 6 botellas 1 l"), és 6 x 1000 ml. Sense dades, mida 0.

Entrada: {"vocabulari": {...}, "productes": [{"id", "s" (supermercat), "n" (nom), "q"}]}
Retorna NOMÉS JSON compacte, una fila per producte i en el mateix ordre:
{"r": [[id, marca, producte, [variants], marca_blanca, unitats, mida, unitat], ...]}
"""


def sense_accents(text):
    text = unicodedata.normalize('NFKD', str(text or '')).encode('ascii', 'ignore').decode()
    return ' '.join(text.lower().replace('-', ' ').split())


def es_marca_blanca(marca, supermercat, segons_gemini):
    m = sense_accents(marca)
    if not m:
        return True   # sense marca: producte propi o genèric del supermercat
    if any(m == b or m.startswith(b + ' ') for b in MARQUES_BLANQUES.get(supermercat, [])):
        return True
    return bool(segons_gemini)


def a_float(valor):
    try:
        return float(str(valor).replace(',', '.'))
    except ValueError:
        return 0.0


def llegir_dades():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = sheet.worksheet('Preus').get_all_records()
    cache = {str(r['nom_original']).strip(): r for r in
             sheet.worksheet('Productes_Normalitzats').get_all_records()
             if str(r.get('nom_original', '')).strip()}
    print(f"Preus: {len(preus)} files | cache v2: {len(cache)} productes")
    per_super = defaultdict(int)
    for f in preus:
        per_super[f['supermercat']] += 1
    print(f"Preus per supermercat: {dict(per_super)}")
    return preus, cache


def cridar(client, vocabulari, lot):
    entrada = {'vocabulari': vocabulari,
               'productes': [{'id': p['id'], 's': p['supermercat'], 'n': p['producte'], 'q': p['quantitat']}
                             for p in lot]}
    config = types.GenerateContentConfig(
        response_mime_type='application/json', temperature=0.0,
        thinking_config=types.ThinkingConfig(thinking_budget=0))
    inici = time.time()
    resp = client.models.generate_content(
        model=MODEL, contents=PROMPT + "\n\n" + json.dumps(entrada, ensure_ascii=False), config=config)
    return json.loads(resp.text).get('r', []), resp.usage_metadata, time.time() - inici


def preu_unitat(p):
    total = p['unitats'] * p['mida']
    if total <= 0:
        return None, ''
    if p['unitat'] == 'ml':
        return p['preu'] / total * 1000, '€/l'
    if p['unitat'] == 'g':
        return p['preu'] / total * 1000, '€/kg'
    return p['preu'] / total, '€/u'


def format_text(p):
    mida = int(p['mida']) if float(p['mida']).is_integer() else p['mida']
    return f"{p['unitats']} x {mida} {p['unitat']}" if p['unitats'] != 1 else f"{mida} {p['unitat']}"


def ordre_barrejat(productes):
    # Alterna supermercats perque cada lot en tingui de tots i el mateix
    # producte quedi repartit en lots diferents (prova dura del vocabulari)
    per_super = defaultdict(list)
    for p in productes:
        per_super[p['supermercat']].append(p)
    resultat = []
    while any(per_super.values()):
        for s in SUPERMERCATS + [k for k in per_super if k not in SUPERMERCATS]:
            if per_super.get(s):
                resultat.append(per_super[s].pop(0))
    return resultat


def processar_categoria(categoria, productes, client, totals):
    print(f"\n{'=' * 100}\n### Categoria {categoria}: {len(productes)} productes")
    vocabulari = {'productes': {}, 'marques': []}   # producte -> [variants conegudes]
    resultats = []
    for num_lot, i in enumerate(range(0, len(productes), MIDA_LOT), start=1):
        lot = productes[i:i + MIDA_LOT]
        try:
            files, us, segons = cridar(client, vocabulari, lot)
        except Exception as e:
            print(f"❌ Error al lot {num_lot}: {type(e).__name__} {str(e)[:300]}")
            if '429' in str(e) or 'spending cap' in str(e).lower():
                return resultats, True
            continue
        sortida = (us.candidates_token_count or 0) + (us.thoughts_token_count or 0)
        totals['entrada'] += us.prompt_token_count or 0
        totals['sortida'] += sortida
        per_id = {str(f[0]): f for f in files if isinstance(f, list) and len(f) >= 8}
        for p in lot:
            f = per_id.get(str(p['id']))
            if not f:
                continue
            _, marca, producte, variants, mb, unitats, mida, unitat = f[:8]
            variants = sorted({str(v).strip().lower() for v in (variants or []) if str(v).strip()})
            r = dict(p, marca=str(marca or '').strip(), producte_n=str(producte or '').strip().lower(),
                     variant=tuple(variants), mb_gemini=mb, lot=num_lot,
                     unitats=a_float(unitats) or 1, mida=a_float(mida), unitat=str(unitat or ''))
            r['unitats'] = int(r['unitats']) if float(r['unitats']).is_integer() else r['unitats']
            resultats.append(r)
            # Amplia el vocabulari per als lots seguents
            conegudes = vocabulari['productes'].setdefault(r['producte_n'], [])
            v = ', '.join(variants)
            if v not in conegudes:
                conegudes.append(v)
            if r['marca'] and r['marca'] not in vocabulari['marques']:
                vocabulari['marques'].append(r['marca'])
        print(f"  lot {num_lot}: {len(lot)} productes, {len(per_id)} respostes, {segons:.1f}s, "
              f"entrada={us.prompt_token_count} sortida={sortida}")
    noms = sorted(vocabulari['productes'])
    print(f"\n  Vocabulari final: {len(noms)} productes diferents")
    for nom in noms:
        print(f"    - {nom}: {vocabulari['productes'][nom]}")
    return resultats, False


def comparar(categoria, resultats):
    # Marques comercials: mateixa marca + producte + variant + tipus d'unitat
    comercials = defaultdict(list)
    blanques = defaultdict(list)
    for r in resultats:
        pu, u = preu_unitat(r)
        if not pu:
            continue
        r['pu'], r['u'] = pu, u
        if es_marca_blanca(r['marca'], r['supermercat'], r['mb_gemini']):
            blanques[(r['producte_n'], r['variant'], u)].append(r)
        else:
            comercials[(sense_accents(r['marca']), r['producte_n'], r['variant'], u)].append(r)

    def mostrar(grups, titol, amb_marca):
        comparables = {k: v for k, v in grups.items() if len({r['supermercat'] for r in v}) >= 2}
        multi_lot = sum(len({r['lot'] for r in v}) > 1 for v in comparables.values())
        print(f"\n  ── {titol} de {categoria}: {len(comparables)} comparables "
              f"({multi_lot} amb productes de lots diferents) de {len(grups)} grups ──")
        ordenats = sorted(comparables.items(), key=lambda g: -len({r['supermercat'] for r in g[1]}))
        for clau, membres in ordenats[:25]:
            marca = f"{membres[0]['marca']} | " if amb_marca else ''
            print(f"  ▶ {marca}{clau[-3] if amb_marca else clau[0]} | "
                  f"{', '.join(clau[-2]) or 'normal'} ({clau[-1]})")
            millor = {}
            for r in membres:
                if r['supermercat'] not in millor or r['pu'] < millor[r['supermercat']]['pu']:
                    millor[r['supermercat']] = r
            for r in sorted(millor.values(), key=lambda r: r['pu']):
                print(f"      {r['supermercat']:<18} {r['pu']:7.2f} {r['u']:<5} lot {r['lot']:<2} "
                      f"{r['marca'] or '(sense marca)':<22} {r['preu']:>6.2f} € {format_text(r):<13} "
                      f"(web: {r['quantitat'] or '-'})  {r['producte']}")
        return len(comparables), multi_lot

    c = mostrar(comercials, 'Marques comercials', True)
    b = mostrar(blanques, 'Marques blanques', False)
    sense_format = sum(1 for r in resultats if not preu_unitat(r)[0])
    print(f"\n  Resum {categoria}: {len(resultats)} productes, {sense_format} sense format, "
          f"comercials comparables {c[0]}, blanques comparables {b[0]}")


def main():
    preus, cache = llegir_dades()
    seleccio = []
    for f in preus:
        nom = str(f.get('producte', '')).strip()
        cat = str(cache.get(nom, {}).get('categoria', '')).strip()
        if cat in CATEGORIES:
            seleccio.append({'id': f"P{len(seleccio)}", 'categoria': cat, 'producte': nom,
                             'supermercat': f.get('supermercat', ''), 'preu': a_float(f.get('preu')),
                             'quantitat': str(f.get('quantitat', '') or '')})
    print(f"Categories {CATEGORIES}: {len(seleccio)} productes")
    for cat in CATEGORIES:
        n = defaultdict(int)
        for p in seleccio:
            if p['categoria'] == cat:
                n[p['supermercat']] += 1
        print(f"  {cat}: {dict(n)}")
    if len(seleccio) > MAX_PRODUCTES:
        print(f"⚠️  Mes de {MAX_PRODUCTES} productes: es processen nomes les primeres categories fins al limit")

    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    totals = {'entrada': 0, 'sortida': 0}
    processats = 0
    for cat in CATEGORIES:
        productes = ordre_barrejat([p for p in seleccio if p['categoria'] == cat])
        if processats + len(productes) > MAX_PRODUCTES:
            print(f"\n⏭️  {cat} ({len(productes)} productes) superaria el limit de {MAX_PRODUCTES}: no es processa")
            continue
        processats += len(productes)
        resultats, aturar = processar_categoria(cat, productes, client, totals)
        comparar(cat, resultats)
        if aturar:
            print("🛑 Error del compte de Gemini: s'atura")
            break

    cost = totals['sortida'] / 1e6 * EUR_PER_M_SORTIDA
    print(f"\nTokens: entrada={totals['entrada']} sortida={totals['sortida']} | "
          f"productes={processats} | cost estimat ~{cost:.2f} € "
          f"(~{cost / max(processats, 1) * 1000:.2f} € per 1.000 productes)")


if __name__ == '__main__':
    main()
