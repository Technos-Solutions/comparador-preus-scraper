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

import inspect
import json
import os
import random
import re
from collections import Counter, defaultdict

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3
from normalitzador_v3 import MarquesBlanques, comparar, llegir_atributs, llegir_preus

NUM = r'(\d+(?:[.,]\d+)?)'
# Unitats que fan servir els scrapers a la columna quantitat -> (unitat del normalitzador, factor)
UNITATS_WEB = {'g': ('g', 1), 'gr': ('g', 1), 'kg': ('g', 1000), 'ml': ('ml', 1), 'cl': ('ml', 10),
               'l': ('ml', 1000), 'u': ('u', 1), 'ud': ('u', 1), 'uds': ('u', 1), 'unidad': ('u', 1),
               'unidades': ('u', 1), 'per paquet': ('u', 1), 'd': ('u', 1)}
# Mides que es poden llegir del nom del producte
UNITATS_NOM = {'g': ('g', 1), 'gr': ('g', 1), 'kg': ('g', 1000), 'ml': ('ml', 1), 'cl': ('ml', 10),
               'l': ('ml', 1000), 'litro': ('ml', 1000), 'litros': ('ml', 1000)}
PARAULES_PACK = (r'x|ud\b|uds\b|unidades|unitats|u\.|latas|llaunes|botellas|botellines|ampolles|briks?|bricks?|'
                 r'sobres|cápsulas|capsulas|càpsules|bolsitas|piezas|rollos|per paquet|tarrinas|vasos|envases|paquetes')


def num(text):
    return float(text.replace(',', '.'))


def quantitat_web(text, nom=''):
    """'6 x 1.5 l' -> ('ml', 9000). None si no es pot llegir."""
    t = str(text or '').lower().replace('aprox.', '').strip().rstrip('.').strip()
    if not t:
        return None
    k = 1
    m = re.fullmatch(NUM + r'\s*x\s*' + NUM + r'\s*(.+)', t)
    if m:
        k, t = num(m.group(1)), m.group(2) + ' ' + m.group(3)
    m = re.fullmatch(NUM + r'\s*(.+?)\.?', t)
    if not m or m.group(2).strip() not in UNITATS_WEB:
        return None
    unitat, factor = UNITATS_WEB[m.group(2).strip()]
    # Dia/Carrefour treuen la quantitat del nom: "66 lavados" acabava com "66 l"
    if unitat == 'ml' and re.search(r'\d+\s*(lavados|rentades|dosis)', nom.lower()):
        return None
    total = k * num(m.group(1)) * factor
    return (unitat, total) if total > 0 else None


def packs_del_nom(nom):
    """Quantitats totals de pack que diu el nom: '24 latas 33 cl' -> {('ml', 7920), ('u', 24)}."""
    t = nom.lower()
    mides = [(num(v), UNITATS_NOM[u]) for v, u in re.findall(NUM + r'\s*(kg|gr|g|ml|cl|litros|litro|l)\b', t)]
    packs = [num(x) for x in re.findall(r'(\d+)\s*(?:' + PARAULES_PACK + ')', t)]
    packs += [num(x) for x in re.findall(r'(?:pack|paquete|caja|estuche|maletín)\s+(?:de\s+)?(\d+)', t)]
    resultat = set()
    for k in packs:
        if k >= 2:
            resultat.add(('u', k))
            for v, (u, f) in mides:
                resultat.add((u, k * v * f))
    return resultat


def quantitat_final(nom, quantitat, a):
    """(unitats, mida, unitat, motiu) per calcular el preu per kg/l/u."""
    gemini = (a['unitats'] or 1) * (a['mida'] or 0)
    w = quantitat_web(quantitat, nom)
    if not w:
        return a['unitats'], a['mida'], a['unitat'], 'gemini: la web no diu la quantitat'
    unitat, total = w
    if unitat != a['unitat']:
        return a['unitats'], a['mida'], a['unitat'], 'gemini: unitats diferents de la web'
    if gemini > 0 and abs(gemini / total - 1) < 0.03:
        return a['unitats'], a['mida'], a['unitat'], 'iguals'
    if gemini > total * 1.5 and any(u == unitat and abs(gemini / v - 1) < 0.03 for u, v in packs_del_nom(nom)):
        return a['unitats'], a['mida'], a['unitat'], 'gemini: pack que diu el nom'
    return 1, total, unitat, 'web: Gemini discrepa'


def comparar_nou():
    # Mateixa funcio que normalitzador_v3.comparar, nomes canvia d'on surt la quantitat
    font = inspect.getsource(comparar)
    vell = "pu, u = preu_unitat(f['preu'], a['unitats'], a['mida'], a['unitat'])"
    assert font.count(vell) == 1
    font = font.replace(vell, "pu, u = preu_unitat(f['preu'], *quantitat_final(f['producte'], f['quantitat'], a)[:3])")
    espai = dict(vars(nv3), quantitat_final=quantitat_final)
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

    # 1. D'on surt la quantitat amb la regla nova
    motius, exemples = defaultdict(Counter), defaultdict(list)
    for f in preus:
        a = atributs.get((f['supermercat'], f['producte']))
        if not a or not a['producte']:
            continue
        unitats, mida, unitat, motiu = quantitat_final(f['producte'], f['quantitat'], a)
        motius[f['supermercat']][motiu] += 1
        if motiu.startswith('web') or motiu.endswith('nom'):
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
    vell = {tuple(f[:6]): f for f in comparar(preus, atributs, marques)}
    nou = {tuple(f[:6]): f for f in comparar_nou()(preus, atributs, marques)}
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
                 'Café cápsulas Colombia Starbucks', 'Lombarda 1 Kg', 'Sopa juliana Trevijano'):
        for f in preus:
            a = atributs.get((f['supermercat'], f['producte']))
            if a and text.lower() in f['producte'].lower():
                antic = nv3.preu_unitat(f['preu'], a['unitats'], a['mida'], a['unitat'])
                q = quantitat_final(f['producte'], f['quantitat'], a)
                nou_pu = nv3.preu_unitat(f['preu'], *q[:3])
                print(f"   {f['supermercat'][:10]:<10} | {f['producte'][:50]:<50} | {f['preu']}€ {f['quantitat']!r} | "
                      f"ara {antic[0] and round(antic[0], 2)}{antic[1]} -> {nou_pu[0] and round(nou_pu[0], 2)}{nou_pu[1]} ({q[3]})")


if __name__ == '__main__':
    main()
