# debug_proves_gamma_sabors.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu
# enlloc). Crida Gemini per a les categories de PROVA (cost estimat < 0,50 €).
#
# Dues proves (INCIDENCIES items 24 i 29):
#   1. GAMMA: una crida a part que nomes afegeix la gamma o linia comercial (Ristorante, Casa di Mama,
#      Qualità Oro...) als productes de marca de fabricant, SENSE tornar a extreure la resta d'atributs
#      (la prova del 06/11 ho feia tot de nou i es perdien variants).
#   2. SABORS: Gemini unifica les variants que volen dir el mateix ("4 formatges" = "quatre formatges").
# Per a cada prova compara les comparacions de les categories de prova abans i despres.
import json
import os
import time
from collections import Counter, defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3

PROVA = ['cafe', 'congelat']
MIDA_LOT = 100

PROMPT_GAMMA = """Ets una persona que compara preus entre supermercats. Per a cada producte d'una marca de
fabricant, digues la seva GAMMA: el nom propi de la línia o model comercial que el distingeix d'altres
productes de la mateixa marca i del mateix tipus. Exemples: Dr. Oetker -> "Ristorante", "Casa di Mama",
"Tradizionale", "Rústica", "Piccola"; Lavazza -> "Qualità Oro", "Crema e Gusto"; Marcilla -> "Gran Aroma",
"Creme Express"; L'Or -> "Onyx", "Sontuoso"; Findus -> "Delicias del Mar".
- Escriu-la sempre igual i sense la marca. Si a "gammes" hi ha una gamma equivalent per a la marca, fes
  servir exactament aquella.
- Una gamma és un nom comercial propi. NO són gammes: sabors, ingredients, tipus, intensitats, mides,
  formats, ni res que ja surti a "p" (producte) o a "v" (variant): "tonyina", "descafeïnat", "intens",
  "natural", "en càpsules", "familiar", "sense gluten" NO són gammes.
- "" si el nom no diu cap gamma.
Entrada: {"gammes": {marca: [gammes ja fetes servir]}, "productes": [{"id", "n" (nom a la web), "m" (marca), "p", "v"}]}
Retorna NOMÉS JSON compacte, una fila per producte: {"r": [[id, gamma], ...]}"""

PROMPT_SABORS = """Ets una persona que compara preus entre supermercats. Per a cada grup tens un tipus de
producte ("p") i les variants que s'hi han fet servir ("v"). Una variant és una llista de trets separats
per comes (sabor, ingredient, tipus...). Detecta les variants que volen dir EXACTAMENT el mateix per a qui
compra però estan escrites diferent: números en xifres o en lletres ("4 formatges" = "quatre formatges"),
català/castellà o italià ("tonyina" = "tonno"), sinònims exactes, singular/plural, ordre o comes diferents.
- NO ajuntis variants que siguin productes diferents encara que s'assemblin: "pernil" (curat) i "pernil
  dolç" (cuit) són diferents; "formatge" i "quatre formatges" també; "intens" i "extra intens" també.
- Per a cada variant que s'hagi d'unificar, dona la forma canònica (una de les que ja hi ha al grup, la
  més clara en català).
Entrada: {"grups": [{"id", "p", "v": [variants]}]}
Retorna NOMÉS JSON compacte, només les variants que canvien: {"r": [[id_grup, variant, variant_canonica], ...]}"""


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = nv3.llegir_preus(sheet)
    atributs = nv3.llegir_atributs(sheet.worksheet('Productes_Atributs'))
    marques = nv3.MarquesBlanques(sheet.worksheet('Marques_Blanques').get_all_records(), atributs)
    ref = nv3.referencies_preu(preus, atributs)
    sa = nv3.sense_accents

    files = []
    for f in preus:
        a = atributs.get((f['supermercat'], f['producte']))
        if not a or not a['producte'] or (a['categoria'] not in PROVA and 'pizza' not in a['producte'].lower()):
            continue
        pu, u = nv3.preu_unitat(f['preu'], *nv3.quantitat_comparable(
            f['producte'], f['quantitat'], a, f['preu'], ref.get((a['categoria'], a['unitat'])))[:3])
        if not pu:
            continue
        blanca = marques.es_blanca(a['marca'], f['supermercat'], a['marca_blanca'])
        files.append(dict(id=f"P{len(files)}", s=f['supermercat'], n=f['producte'], preu=f['preu'], pu=pu, u=u,
                          blanca=blanca, a=a, gamma='', variant=a['variant']))
    print(f"Productes de prova ({', '.join(PROVA)}): {len(files)} | de marca de fabricant: {sum(1 for x in files if not x['blanca'])}")

    def grups(clau):
        g = defaultdict(list)
        for x in files:
            g[clau(x)].append(x)
        return g

    def comparables(g):
        return {k: v for k, v in g.items() if len({x['s'] for x in v}) > 1}

    NUMS = {'2': 'dos', '3': 'tres', '4': 'quatre', '5': 'cinc', '6': 'sis', '7': 'set', '8': 'vuit', '9': 'nou', '10': 'deu'}

    def variant_codi(v):
        # sense Gemini: numeros en lletres, trets sense repetir i en ordre ("4 formatges" = "quatre formatges")
        trets = {' '.join(NUMS.get(w, w) for w in sa(t).split()) for t in str(v or '').split(',')}
        return ', '.join(sorted(t for t in trets if t))

    def clau_com(x, gamma=False, variant=None, regla_gamma='A'):
        a = x['a']
        v = sa(x['variant'] if variant is None else variant)
        if x['blanca']:
            return ('B', a['categoria'], sa(a['producte']), v, x['u'])
        if gamma and regla_gamma == 'B':
            # B: la gamma nomes separa si tots els productes del grup en tenen
            return ('C', sa(a['marca']), sa(a['producte']), v, x['u'], x.get('gamma_b', ''))
        return ('C', sa(a['marca']), sa(a['producte']), v, x['u']) + ((sa(x['gamma']),) if gamma else ())

    abans = comparables(grups(clau_com))
    print(f"Comparacions ara a les categories de prova: {len(abans)} "
          f"(comercials {sum(1 for k in abans if k[0] == 'C')}, blanques {sum(1 for k in abans if k[0] == 'B')})")
    gemini = nv3.ClientGemini(os.environ['GEMINI_API_KEY'])
    inici = time.time()

    # ── PROVA 1: GAMMA ───────────────────────────────────────────────────────
    print("\n========== PROVA 1: GAMMA ==========")
    comercials = sorted([x for x in files if not x['blanca']], key=lambda x: (sa(x['a']['marca']), x['n']))
    gammes = defaultdict(Counter)
    lot = []
    def envia(lot):
        dades = {'gammes': {m: [g for g, _ in c.most_common(20)] for m, c in gammes.items()
                            if m in {x['a']['marca'] for x in lot}},
                 'productes': [{'id': x['id'], 'n': x['n'], 'm': x['a']['marca'], 'p': x['a']['producte'],
                                'v': x['a']['variant']} for x in lot]}
        per_id = {x['id']: x for x in lot}
        resposta = gemini.cridar(PROMPT_GAMMA, dades) or gemini.cridar(PROMPT_GAMMA, dades)
        for r in resposta:
            if isinstance(r, list) and len(r) >= 2 and str(r[0]) in per_id:
                x = per_id[str(r[0])]
                x['gamma'] = str(r[1] or '').strip()
                if x['gamma']:
                    gammes[x['a']['marca']][x['gamma']] += 1
    for x in comercials:
        # lots per marca: totes les d'una marca juntes ajuden que la gamma s'escrigui igual
        if lot and len(lot) >= MIDA_LOT and sa(lot[-1]['a']['marca']) != sa(x['a']['marca']):
            envia(lot); lot = []
        lot.append(x)
    if lot:
        envia(lot)
    amb = [x for x in comercials if x['gamma']]
    print(f"Productes amb gamma: {len(amb)}/{len(comercials)} | tokens entrada {gemini.tokens_entrada} sortida {gemini.tokens_sortida}")
    print("Gammes per marca (les 20 marques amb mes productes amb gamma):")
    for m, c in sorted(gammes.items(), key=lambda kv: -sum(kv[1].values()))[:20]:
        print(f"   {m}: {dict(c.most_common(10))}")
    despres = comparables(grups(lambda x: clau_com(x, gamma=True)))
    print(f"Comparacions: abans {len(abans)} | amb gamma (regla A: qualsevol diferencia separa) {len(despres)}")
    for k, v in grups(clau_com).items():
        if k[0] == 'C':
            tots = all(x['gamma'] for x in v)
            for x in v:
                x['gamma_b'] = sa(x['gamma']) if tots else ''
    despres_b = comparables(grups(lambda x: clau_com(x, gamma=True, regla_gamma='B')))
    separats_b = [k for k, v in abans.items() if k[0] == 'C' and len({x['gamma_b'] for x in v}) > 1]
    print(f"Regla B (nomes separa si tots tenen gamma): {len(despres_b)} comparacions | grups separats {len(separats_b)}")
    for k in separats_b[:20]:
        v = abans[k]
        detall = '; '.join(f"{x['s'][:9]} {x['gamma']} {x['pu']:.2f}" for x in sorted(v, key=lambda x: x['gamma']))
        print(f"   B separa: {k[1]} | {k[2]} {k[3]} | {detall[:220]}")
    # Grups d'abans que la gamma separa
    separats, perduts = [], []
    for k, v in abans.items():
        if k[0] != 'C':
            continue
        gs = {sa(x['gamma']) for x in v}
        if len(gs) > 1:
            sub = defaultdict(set)
            for x in v:
                sub[sa(x['gamma'])].add(x['s'])
            (separats if any(len(s) > 1 for s in sub.values()) else perduts).append((k, v))
    print(f"Comparacions que la gamma separa en linies diferents: {len(separats) + len(perduts)} "
          f"(segueixen comparables {len(separats)}, ja no es comparen {len(perduts)})")
    print("Exemples de comparacions separades (abans barrejaven gammes):")
    for k, v in (separats + perduts)[:25]:
        detall = '; '.join(f"{x['s'][:9]} {x['gamma'] or '-'} {x['pu']:.2f}" for x in sorted(v, key=lambda x: x['gamma']))
        print(f"   {k[1]} | {k[2]} {k[3]} | {detall[:230]}")

    # ── PROVA 2: SABORS ──────────────────────────────────────────────────────
    print("\n========== PROVA 2: SABORS ==========")
    t0e, t0s = gemini.tokens_entrada, gemini.tokens_sortida
    per_producte = defaultdict(set)
    for x in files:
        if x['variant']:
            per_producte[('', x['a']['producte'].lower())].add(x['variant'])
    llista = [(f"G{i}", k, sorted(v)) for i, (k, v) in enumerate(sorted(per_producte.items())) if len(v) > 1]
    canonica = {}
    for i in range(0, len(llista), 40):
        lot = llista[i:i + 40]
        idx = {g: k for g, k, _ in lot}
        for r in gemini.cridar(PROMPT_SABORS, {'grups': [{'id': g, 'p': k[1], 'v': v} for g, k, v in lot]}):
            if isinstance(r, list) and len(r) >= 3 and str(r[0]) in idx and str(r[1]) != str(r[2]):
                canonica[(idx[str(r[0])], str(r[1]))] = str(r[2])
    print(f"Grups producte amb 2+ variants: {len(llista)} | variants unificades: {len(canonica)} | "
          f"tokens entrada {gemini.tokens_entrada - t0e} sortida {gemini.tokens_sortida - t0s}")
    print("Totes les unificacions proposades:")
    for (k, v), c in sorted(canonica.items()):
        print(f"   {k[1]}: {v!r} -> {c!r}")
    def var_nova(x):
        return canonica.get((('', x['a']['producte'].lower()), x['variant']), x['variant'])
    despres2 = comparables(grups(lambda x: clau_com(x, variant=var_nova(x))))
    claus_abans = set(abans)
    noves = {k: v for k, v in despres2.items() if k not in claus_abans}
    print(f"Comparacions: abans {len(abans)} | amb sabors unificats {len(despres2)} | grups nous o ampliats: {len(noves)}")
    for k, v in list(noves.items())[:30]:
        millors = {}
        for x in v:
            if x['s'] not in millors or x['pu'] < millors[x['s']]['pu']:
                millors[x['s']] = x
        detall = ' | '.join(f"{s[:9]} {x['pu']:.2f} ({x['variant']})" for s, x in millors.items())
        print(f"   {k[1] if k[0] == 'C' else 'marca blanca'} | {k[2]} {k[3]} | {detall[:240]}")

    # Sabors sense Gemini (codi)
    despres3 = comparables(grups(lambda x: clau_com(x, variant=variant_codi(x['variant']))))
    noves3 = {k: v for k, v in despres3.items() if k not in claus_abans}
    print(f"\nSabors amb codi (numeros en lletres, sense repeticions ni ordre): {len(despres3)} comparacions | noves {len(noves3)}")
    for k, v in list(noves3.items())[:30]:
        millors = {}
        for x in v:
            if x['s'] not in millors or x['pu'] < millors[x['s']]['pu']:
                millors[x['s']] = x
        detall = ' | '.join(f"{s[:9]} {x['pu']:.2f} ({x['variant']})" for s, x in millors.items())
        print(f"   {k[1] if k[0] == 'C' else 'marca blanca'} | {k[2]} {k[3]} | {detall[:240]}")
    print("\nVariants de les pizzes Dr. Oetker (per veure 'mozzarella' / 'margarida' / '4 formatges'):")
    vp = Counter((x['s'][:9], x['variant']) for x in files if 'oetker' in x['a']['marca'].lower() and x['a']['producte'].lower() == 'pizza')
    print('   ' + '; '.join(f"{s} {v}" for (s, v), n in sorted(vp.items())))

    cost = gemini.tokens_entrada / 1e6 * 0.30 + gemini.tokens_sortida / 1e6 * 2.5
    print(f"\nTokens totals: entrada {gemini.tokens_entrada} sortida {gemini.tokens_sortida} | "
          f"cost aprox. {cost:.2f} $ | {(time.time() - inici) / 60:.1f} min")


if __name__ == '__main__':
    main()
