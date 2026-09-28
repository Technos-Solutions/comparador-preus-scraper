# debug_gemini_thinking.py — Script de nomes diagnostic, NO escriu res a
# Google Sheets (nomes llegeix la cache). El diagnostic del 28/09/2026 va
# mostrar que gemini-3.5-flash gasta ~6.000 tokens de "raonament" intern per
# lot de 30 productes (dos terços del total, cobrats com a sortida). Aquest
# script compara, amb el mateix prompt de produccio i un lot de 50 (MIDA_LOT):
#   1. Tokens i temps amb el raonament per defecte, reduit o desactivat
#   2. Si la qualitat es mante: coincidencia de nom i categoria amb el
#      resultat per defecte i amb la cache, i exemples de les diferencies
#   3. Estabilitat: cada configuracio es crida dos cops amb el mateix lot,
#      per veure si el nom normalitzat surt igual les dues vegades

import ast
import json
import os
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types

MIDA_MOSTRA = 50
MODEL = 'gemini-3.5-flash'
REPETICIONS = 2

# (nom, ThinkingConfig o None, temperatura)
CONFIGURACIONS = [
    ('defecte', None, 0.1),
    ('level_minimal', {'thinking_level': 'minimal'}, 0.1),
    ('level_low', {'thinking_level': 'low'}, 0.1),
    ('budget_0', {'thinking_budget': 0}, 0.1),
    ('level_minimal_t0', {'thinking_level': 'minimal'}, 0.0),
]


def llegir_prompt():
    # El prompt es llegeix del normalitzador de produccio sense importar-lo
    arbre = ast.parse(open('normalitzador_v2.py', encoding='utf-8').read())
    for node in arbre.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'PROMPT_SISTEMA':
            return ast.literal_eval(node.value)
    raise RuntimeError('PROMPT_SISTEMA no trobat a normalitzador_v2.py')


def mostra_cache():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    ws = gspread.authorize(creds).open('Comparador_Preus_DB').worksheet('Productes_Normalitzats')
    registres = [r for r in ws.get_all_records() if str(r.get('nom_original', '')).strip()]
    print(f"Cache: {len(registres)} productes normalitzats")
    # Mostra repartida per tota la cache (hi ha productes de tots els supermercats)
    pas = max(1, len(registres) // MIDA_MOSTRA)
    return registres[pas // 2::pas][:MIDA_MOSTRA]


def cridar(client, prompt, thinking, temperatura):
    config = types.GenerateContentConfig(
        response_mime_type='application/json', temperature=temperatura,
        thinking_config=types.ThinkingConfig(**thinking) if thinking else None)
    inici = time.time()
    resp = client.models.generate_content(model=MODEL, contents=prompt, config=config)
    return resp.text, resp.usage_metadata, time.time() - inici


def main():
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    mostra = mostra_cache()
    noms = [str(r['nom_original']).strip() for r in mostra]
    prompt = llegir_prompt() + "\n\n" + json.dumps(noms, ensure_ascii=False)
    n = len(noms)

    resultats = {}  # nom_config -> llista de resultats (una per repeticio)
    resum = []
    for nom_cfg, thinking, temperatura in CONFIGURACIONS:
        print(f"\n######## {nom_cfg} (thinking={thinking}, temperatura={temperatura}) ########")
        resultats[nom_cfg] = []
        for rep in range(REPETICIONS):
            try:
                text, us, segons = cridar(client, prompt, thinking, temperatura)
            except Exception as e:
                print(f"❌ Error: {type(e).__name__} {str(e)[:300]}")
                break
            pensament = us.thoughts_token_count or 0
            print(f"  rep {rep + 1}: {segons:.1f}s | entrada={us.prompt_token_count} "
                  f"sortida={us.candidates_token_count} raonament={pensament} total={us.total_token_count}")
            try:
                productes = json.loads(text).get('productes', [])
            except Exception as e:
                print(f"  ❌ JSON invalid: {e} | {text[:200]!r}")
                continue
            if len(productes) != n:
                print(f"  ⚠️  Ha retornat {len(productes)} de {n}")
                continue
            resultats[nom_cfg].append(productes)
            resum.append((nom_cfg, rep + 1, segons, us.prompt_token_count,
                          us.candidates_token_count, pensament, us.total_token_count))

    print("\n######## Resum de tokens (per lot de %d productes) ########" % n)
    print(f"{'config':<18}{'rep':>4}{'segons':>8}{'entrada':>9}{'sortida':>9}{'raonam.':>9}{'total':>8}")
    for fila in resum:
        print(f"{fila[0]:<18}{fila[1]:>4}{fila[2]:>8.1f}{fila[3]:>9}{fila[4]:>9}{fila[5]:>9}{fila[6]:>8}")

    print("\n######## Coincidencies sobre %d ########" % n)
    referencia = (resultats.get('defecte') or [None])[0]
    for nom_cfg, llista in resultats.items():
        if not llista:
            print(f"{nom_cfg:<18} sense resultats")
            continue
        r = llista[0]
        cache_nom = sum(str(mostra[i]['nom_normalitzat']) == r[i].get('nom_normalitzat') for i in range(n))
        cache_cat = sum(str(mostra[i]['categoria']) == r[i].get('categoria') for i in range(n))
        text = f"{nom_cfg:<18} cache: nom {cache_nom:>2} cat {cache_cat:>2}"
        if referencia:
            ref_nom = sum(referencia[i].get('nom_normalitzat') == r[i].get('nom_normalitzat') for i in range(n))
            ref_cat = sum(referencia[i].get('categoria') == r[i].get('categoria') for i in range(n))
            text += f" | defecte: nom {ref_nom:>2} cat {ref_cat:>2}"
        if len(llista) > 1:
            est_nom = sum(llista[0][i].get('nom_normalitzat') == llista[1][i].get('nom_normalitzat') for i in range(n))
            est_cat = sum(llista[0][i].get('categoria') == llista[1][i].get('categoria') for i in range(n))
            text += f" | rep1=rep2: nom {est_nom:>2} cat {est_cat:>2}"
        print(text)

    print("\n######## Detall per producte (primera repeticio de cada config) ########")
    for i, nom in enumerate(noms):
        print(f"- {nom!r}\n    {'cache':<18} {str(mostra[i]['nom_normalitzat'])!r} [{mostra[i]['categoria']}]")
        for nom_cfg, llista in resultats.items():
            if llista:
                p = llista[0][i]
                print(f"    {nom_cfg:<18} {p.get('nom_normalitzat')!r} [{p.get('categoria')}] marca={p.get('marca')!r}")


if __name__ == '__main__':
    main()
