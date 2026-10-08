# debug_bonpreu_api3.py — Script de nomes diagnostic, NO toca Google Sheets ni
# el scraper de produccio.
#
# Resultats anteriors (08/10):
#   - debug_bonpreu_api2.py: window.__INITIAL_STATE__ te la llista d'ids de la
#     fulla (data.products.catalogue.data.productGroups[].products) i el detall
#     dels primers ~30 (productEntities: nom, marca, preu, preu per unitat).
#     Repetir el POST /api/webproductpagews/v6/products amb fetch des de la
#     pagina retorna 403 (proteccio AWS WAF: falten capcaleres de la pagina).
# Aquest diagnostic, a la fulla "packs" de llet (90 productes de veritat):
#   1. Compta tots els ids de tots els productGroups de l'estat inicial
#   2. Escolta el transit de xarxa del navegador (logs de rendiment de Chrome)
#      mentre es fa scroll: capcaleres i cos dels POST de productes de la
#      pagina i les seves respostes JSON (quants productes amb nom i preu)
#   3. Repeteix un POST amb les MATEIXES capcaleres i tots els ids pendents,
#      per veure si una sola crida dona tota la fulla

import ast
import functools
import json
import re
import time

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

FULLA = ('ctics', ['llets-i-begudes-vegetals', 'packs'])

JS_IDS = """
const s = window.__INITIAL_STATE__ || {};
const cat = (((s.data || {}).products || {}).catalogue || {}).data || {};
const grups = (cat.productGroups || []).map(g => ({nom: g.name || g.title || g.id || '', n: (g.products || []).length}));
const ids = [];
(cat.productGroups || []).forEach(g => (g.products || []).forEach(id => { if (id && !ids.includes(id)) ids.push(id); }));
const entitats = Object.keys(((s.data || {}).products || {}).productEntities || {});
return {grups: grups, ids: ids, entitats: entitats, claus_cat: Object.keys(cat),
        total: cat.totalProducts || cat.total || cat.productCount || null};
"""

JS_POST = """
const [url, cos, capcaleres] = [arguments[0], arguments[1], arguments[2]];
const done = arguments[arguments.length - 1];
fetch(url, {method: 'POST', credentials: 'include', headers: capcaleres, body: cos})
  .then(r => r.text().then(t => done([r.status, t.length, t])))
  .catch(e => done([0, 0, String(e)]));
"""


def carregar_classe():
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    for node in ast.parse(font).body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            # El mateix driver de produccio, pero amb els logs de rendiment (xarxa) activats
            espai = {'SeleniumBaseDriver': functools.partial(SeleniumBaseDriver, log_cdp=True),
                     'By': By, 'time': time, 're': re}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


BonPreuEsclatScraper = carregar_classe()


def productes_de_resposta(dades):
    # Busca productes (dicts amb productId i name) dins d'una resposta JSON
    trobats = {}

    def recorre(o):
        if isinstance(o, dict):
            if o.get('productId') and o.get('name'):
                preu = ((o.get('price') or {}).get('current') or {}).get('amount')
                trobats[o['productId']] = (o['name'], preu)
            for v in o.values():
                recorre(v)
        elif isinstance(o, list):
            for v in o:
                recorre(v)
    recorre(dades)
    return trobats


def main():
    scraper = BonPreuEsclatScraper(categories_filtre=[FULLA[0]])
    scraper._crear_driver_nou()
    d = scraper.driver
    principals = [(n.lower(), u) for n, u in scraper.descobrir_categories()]
    url = next((u for n, u in principals if FULLA[0] in n), None)
    for slug in FULLA[1]:
        d.get(url)
        time.sleep(3)
        url = next((u for _, u in scraper.get_subcategories(url) if u.rstrip('/').split('/')[-2] == slug), None)
    print(f"Fulla: {url}")

    d.get_log('performance')   # buida els logs anteriors
    d.get(url)
    time.sleep(5)

    print("\n######## 1. Ids a l'estat inicial ########")
    estat = d.execute_script(JS_IDS)
    print(f"Grups: {estat['grups']}")
    print(f"Ids diferents: {len(estat['ids'])} | amb detall a l'estat inicial: {len(estat['entitats'])}")
    print(f"Claus de catalogue.data: {estat['claus_cat']} | total indicat: {estat['total']}")
    tots = {}
    for _ in range(30):
        d.execute_script('window.scrollBy(0, 800)')
        time.sleep(0.6)
    time.sleep(2)

    print("\n######## 2. Transit de xarxa de productes ########")
    peticions = {}
    for entrada in d.get_log('performance'):
        try:
            msg = json.loads(entrada['message'])['message']
        except Exception:
            continue
        p = msg.get('params', {})
        if msg.get('method') == 'Network.requestWillBeSent' and 'webproductpagews' in p.get('request', {}).get('url', ''):
            peticions[p['requestId']] = p['request']
        elif msg.get('method') == 'Network.requestWillBeSentExtraInfo' and p.get('requestId') in peticions:
            peticions[p['requestId']]['capcaleres_reals'] = p.get('headers', {})
    print(f"Peticions a webproductpagews: {len(peticions)}")
    primera = None
    for rid, req in peticions.items():
        cos = req.get('postData') or ''
        print(f"\n  {req.get('method')} {req['url'][:200]}")
        print(f"   cos: {cos[:400]}")
        capcaleres = req.get('capcaleres_reals') or req.get('headers') or {}
        print(f"   capcaleres: {sorted(capcaleres)}")
        try:
            body = d.execute_cdp_cmd('Network.getResponseBody', {'requestId': rid})
            dades = json.loads(body.get('body') or '{}')
            trobats = productes_de_resposta(dades)
            tots.update(trobats)
            print(f"   resposta: {len(trobats)} productes amb nom")
        except Exception as e:
            print(f"   resposta no disponible: {str(e)[:150]}")
        if req.get('method') == 'POST' and not primera:
            primera = req

    print(f"\nProductes amb nom vistos a les respostes: {len(tots)}")
    for pid, (nom, preu) in list(tots.items())[:5]:
        print(f"   {preu} € | {nom}")

    print("\n######## 3. Un sol POST amb les capcaleres de la pagina ########")
    if not primera:
        print("No s'ha capturat cap POST de la pagina")
    else:
        pendents = [i for i in estat['ids'] if i and i not in tots and i not in estat['entitats']]
        capcaleres = {k: v for k, v in (primera.get('capcaleres_reals') or primera.get('headers') or {}).items()
                      if not k.startswith(':') and k.lower() not in ('content-length', 'cookie', 'host',
                                                                         'accept-encoding', 'connection')}
        try:
            original = json.loads(primera.get('postData') or '{}')
        except Exception:
            original = {}
        clau = next((k for k, v in original.items() if isinstance(v, list)), 'productIds') if isinstance(original, dict) else None
        cos = dict(original) if isinstance(original, dict) else {}
        cos[clau or 'productIds'] = pendents or estat['ids']
        status, mida, text = d.execute_async_script(JS_POST, primera['url'], json.dumps(cos), capcaleres)
        print(f"Ids demanats: {len(cos[clau or 'productIds'])} | status={status} mida={mida}")
        if status == 200:
            try:
                trobats = productes_de_resposta(json.loads(text))
                print(f"Productes retornats amb nom: {len(trobats)}")
                for pid, (nom, preu) in list(trobats.items())[:5]:
                    print(f"   {preu} € | {nom}")
            except Exception as e:
                print(f"No es JSON: {e} | {text[:300]}")
        else:
            print(text[:400])

    try:
        d.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()
