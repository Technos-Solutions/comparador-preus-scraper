# debug_gemini_genai.py — Script de nomes diagnostic, NO escriu res a
# Google Sheets (nomes llegeix la cache). Abans de migrar normalitzador_v2.py
# del paquet google.generativeai (sense suport des del 2026) al nou
# google.genai, valida amb crides reals:
#   1. Que el compte de Gemini funciona (credits recarregats el 28/09/2026)
#   2. Que el SDK nou dona el mateix resultat que el vell amb el mateix
#      prompt, model i configuracio (i que tots dos quadren amb la cache)
#   3. Quants tokens gasta un lot, per estimar el cost setmanal
#   4. Com arriben els errors al SDK nou (codi, estat, missatge), per
#      adaptar-hi la deteccio d'errors del compte i de quota

import ast
import json
import os
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials

MIDA_MOSTRA = 30
MODEL = 'gemini-3.5-flash'


def llegir_prompt():
    # El prompt es llegeix del normalitzador de produccio (sense importar-lo,
    # perque en importar-lo es connecta a Sheets i comenca a normalitzar)
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
    pas = max(1, len(registres) // MIDA_MOSTRA)
    return registres[::pas][:MIDA_MOSTRA]


def descriure_error(e):
    atributs = {a: getattr(e, a) for a in ('code', 'status', 'message') if hasattr(e, a)}
    return f"{type(e).__module__}.{type(e).__name__} {atributs} | str: {str(e)[:300]}"


def amb_sdk_vell(prompt):
    import google.generativeai as genai_vell
    genai_vell.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai_vell.GenerativeModel(
        model_name=MODEL,
        generation_config={"response_mime_type": "application/json", "temperature": 0.1})
    inici = time.time()
    resp = model.generate_content(prompt)
    return resp.text, resp.usage_metadata, time.time() - inici


def amb_sdk_nou(prompt):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    inici = time.time()
    resp = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.1))
    return resp.text, resp.usage_metadata, time.time() - inici


def provar(nom_sdk, funcio, prompt, n):
    print(f"\n######## SDK {nom_sdk} ########")
    try:
        text, us, segons = funcio(prompt)
    except Exception as e:
        print(f"❌ Error: {descriure_error(e)}")
        return None
    print(f"✅ Resposta en {segons:.1f}s | tokens entrada={us.prompt_token_count} "
          f"sortida={us.candidates_token_count} total={us.total_token_count}")
    try:
        productes = json.loads(text).get('productes', [])
    except Exception as e:
        print(f"❌ JSON invalid: {e} | {text[:300]!r}")
        return None
    print(f"Productes retornats: {len(productes)} de {n}")
    return productes if len(productes) == n else None


def main():
    prompt_sistema = llegir_prompt()
    mostra = mostra_cache()
    noms = [str(r['nom_original']).strip() for r in mostra]
    prompt = prompt_sistema + "\n\n" + json.dumps(noms, ensure_ascii=False)

    vell = provar('vell (google.generativeai)', amb_sdk_vell, prompt, len(noms))
    nou = provar('nou (google.genai)', amb_sdk_nou, prompt, len(noms))

    print("\n######## Comparacio (cache | vell | nou) ########")
    iguals = {'vell_nou_nom': 0, 'vell_nou_cat': 0, 'cache_nou_nom': 0, 'cache_nou_cat': 0}
    for i, r in enumerate(mostra):
        v = vell[i] if vell else {}
        n = nou[i] if nou else {}
        if v and n:
            iguals['vell_nou_nom'] += v.get('nom_normalitzat') == n.get('nom_normalitzat')
            iguals['vell_nou_cat'] += v.get('categoria') == n.get('categoria')
        if n:
            iguals['cache_nou_nom'] += str(r['nom_normalitzat']) == n.get('nom_normalitzat')
            iguals['cache_nou_cat'] += str(r['categoria']) == n.get('categoria')
        print(f"- {noms[i]!r}\n    cache: {r['nom_normalitzat']!r} [{r['categoria']}]"
              f"\n    vell:  {v.get('nom_normalitzat')!r} [{v.get('categoria')}]"
              f"\n    nou:   {n.get('nom_normalitzat')!r} [{n.get('categoria')}]")
    print(f"\nCoincidencies sobre {len(noms)}: {iguals}")

    print("\n######## Error amb clau falsa (forma de l'error al SDK nou) ########")
    from google import genai
    try:
        genai.Client(api_key='clau-falsa-diagnostic').models.generate_content(model=MODEL, contents='hola')
    except Exception as e:
        print(descriure_error(e))


if __name__ == '__main__':
    main()
