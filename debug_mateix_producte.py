# debug_mateix_producte.py — Script de nomes diagnostic, NO toca Google Sheets.
# Prova una manera de comparar que imita com ho fa una persona. Una persona
# mira els productes de tots els supermercats alhora i, per a cadascun, en
# treu la marca, el tipus de producte, la variant (zero, light, sense
# cafeina...) i el format (2 x 2 l). Dos productes son el mateix si tenen la
# mateixa marca, tipus i variant; el preu es compara pel mateix format o per €/l.
#
# Diferencies amb normalitzador_v2.py:
#   - Gemini veu tota una familia de productes candidats en una sola crida
#     (tots els Coca-Cola dels 5 supermercats), no lots barrejats de 50, i per
#     tant dona el mateix nom als productes equivalents
#   - Retorna atributs separats, no un nom lliure en catala
#   - Tambe retorna el format (unitats x mida) per calcular €/l i €/kg
# Les dades son una foto de Preus_Temp del 27/09/2026 amb les 5 parts
# (debug_families_productes.json), perque ara mateix la Part 3 esta
# reescrivint Preus_Temp.

import json
import os
import sys
import time
from collections import defaultdict

from google import genai
from google.genai import types

MODEL = 'gemini-3.5-flash'
SIGLES = {'Mercadona': 'MER', 'Bon Àrea': 'BAR', 'Dia': 'DIA',
          'Bon Preu / Esclat': 'BPR', 'Carrefour': 'CRF'}

PROMPT = """Ets una persona que compara preus entre supermercats (Mercadona, Bon Àrea,
Dia, Bon Preu/Esclat i Carrefour). Reps una llista JSON de productes de diversos
supermercats que potser són el mateix producte. Cada supermercat escriu el nom a
la seva manera (en català o castellà, amb o sense marca, amb el format dins del nom).

Per a CADA producte, extreu-ne els atributs tal com ho faria una persona:
- "marca": marca comercial, sempre escrita igual per a la mateixa marca
  (p. ex. "Coca-Cola", "Nutella", "Hacendado"). Si no n'hi ha, "".
- "producte": què és, en català, genèric i curt (p. ex. "refresc de cola",
  "crema de cacau i avellanes", "llet", "oli d'oliva", "ous").
- "variant": llista dels trets que el fan un producte DIFERENT dins la mateixa
  marca i producte, en català i minúscules (p. ex. ["zero sucre"],
  ["zero sucre", "sense cafeïna"], ["light"], ["sencera"], ["verge extra"],
  ["talla l", "gallines camperes"]). Si és la versió normal o "original", [].
  NO hi posis el format, l'envàs ni la quantitat.
- "unitats": quantes unitats té el pack (1 si no és un pack).
- "mida": mida de cada unitat, com a número.
- "unitat": "ml", "g" o "u" (per a productes que es venen per peces, p. ex. ous).
  Converteix l → ml, cl → ml, kg → g.

MOLT IMPORTANT: si dos productes de supermercats diferents són el mateix
producte (mateixa marca, mateix producte i mateixa variant), han de tenir
EXACTAMENT els mateixos textos a "marca", "producte" i "variant", encara que
el format sigui diferent. Fes servir el mateix vocabulari per a tots.

Retorna només JSON: {"productes": [{"id": "...", "marca": "...", "producte": "...",
"variant": [...], "unitats": 1, "mida": 0, "unitat": "ml"}, ...]}, un element per
cada id d'entrada.
"""


def cridar(client, entrada, thinking):
    config = types.GenerateContentConfig(
        response_mime_type='application/json', temperature=0.0,
        thinking_config=types.ThinkingConfig(**thinking) if thinking is not None else None)
    inici = time.time()
    resp = client.models.generate_content(
        model=MODEL, contents=PROMPT + "\n\n" + json.dumps(entrada, ensure_ascii=False),
        config=config)
    return json.loads(resp.text).get('productes', []), resp.usage_metadata, time.time() - inici


def preu_unitat(p, a):
    # €/l, €/kg o €/u a partir del format que ha extret Gemini
    try:
        total = float(a.get('unitats') or 1) * float(a.get('mida') or 0)
    except (TypeError, ValueError):
        return None, ''
    if total <= 0:
        return None, ''
    unitat = a.get('unitat')
    if unitat == 'ml':
        return p['preu'] / total * 1000, '€/l'
    if unitat == 'g':
        return p['preu'] / total * 1000, '€/kg'
    return p['preu'] / total, '€/u'


def format_text(a):
    unitats, mida = a.get('unitats') or 1, a.get('mida')
    mida = int(mida) if isinstance(mida, float) and mida.is_integer() else mida
    return f"{unitats} x {mida} {a.get('unitat', '')}" if unitats != 1 else f"{mida} {a.get('unitat', '')}"


def analitzar(nom_familia, productes, client, thinking, etiqueta):
    entrada, per_id = [], {}
    for i, p in enumerate(productes):
        pid = f"{SIGLES.get(p['supermercat'], 'XXX')}{i}"
        per_id[pid] = p
        entrada.append({'id': pid, 'supermercat': p['supermercat'], 'nom': p['producte']})

    print(f"\n{'=' * 100}\n### {nom_familia} [{etiqueta}]: {len(productes)} productes")
    try:
        resultat, us, segons = cridar(client, entrada, thinking)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__} {str(e)[:300]}")
        return None
    print(f"{segons:.1f}s | entrada={us.prompt_token_count} sortida={us.candidates_token_count} "
          f"raonament={us.thoughts_token_count or 0}")
    atributs = {r.get('id'): r for r in resultat}
    falten = [pid for pid in per_id if pid not in atributs]
    if falten:
        print(f"⚠️  Falten {len(falten)} ids a la resposta: {falten[:10]}")

    # Mateix producte = mateixa marca + producte + variant (sense comptar el format)
    grups = defaultdict(list)
    for pid, p in per_id.items():
        a = atributs.get(pid)
        if not a:
            continue
        clau = (a.get('marca', ''), a.get('producte', ''), tuple(sorted(a.get('variant') or [])))
        grups[clau].append((p, a))

    comparables = 0
    for clau, membres in sorted(grups.items(), key=lambda g: (-len({p['supermercat'] for p, _ in g[1]}), g[0])):
        supers = {p['supermercat'] for p, _ in membres}
        comparables += len(supers) >= 2
        variant = ', '.join(clau[2]) or 'original'
        print(f"\n  ▶ {clau[0] or '(sense marca)'} | {clau[1]} | {variant}  —  {len(supers)} supermercats")
        for p, a in sorted(membres, key=lambda m: (preu_unitat(*m)[0] or 1e9)):
            pu, u = preu_unitat(p, a)
            pu_text = f"{pu:7.2f} {u}" if pu else "      ?    "
            print(f"      {p['supermercat']:<18} {p['preu']:>6.2f} € {format_text(a):<14} {pu_text}  "
                  f"(web: {p['quantitat'] or '-'})  {p['producte']}")
    print(f"\n  Resum {nom_familia} [{etiqueta}]: {len(grups)} productes diferents, "
          f"{comparables} presents a 2 o més supermercats")
    return us


def main():
    dades = json.load(open('debug_families_productes.json', encoding='utf-8'))
    print(f"Dades: {dades['font']}")
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    families = sys.argv[1:] or list(dades['families'])

    total_entrada = total_sortida = 0
    for nom in families:
        us = analitzar(nom, dades['families'][nom], client, {'thinking_budget': 0}, 'sense raonament')
        if us:
            total_entrada += us.prompt_token_count
            total_sortida += (us.candidates_token_count or 0) + (us.thoughts_token_count or 0)

    # Control: la familia de l'exemple (Coca-Cola) tambe amb el raonament per defecte
    if 'coca_cola' in families:
        us = analitzar('coca_cola', dades['families']['coca_cola'], client, None, 'amb raonament')
        if us:
            total_entrada += us.prompt_token_count
            total_sortida += (us.candidates_token_count or 0) + (us.thoughts_token_count or 0)

    print(f"\nTokens totals: entrada={total_entrada} sortida+raonament={total_sortida}")


if __name__ == '__main__':
    main()
