# debug_bonpreu_api4.py — Script de nomes diagnostic, NO toca Google Sheets ni
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

# Resultat de debug_bonpreu_api3.py (08/10): l'estat inicial te els 90 ids de
# "packs" (totalProducts=90) i el detall de 30; la pagina demana la resta amb
# PUT /api/webproductpagews/v6/products (cos = llista d'ids, 24 per crida) i
# capcaleres x-csrf-token, client-route-id, page-view-id... Aquest diagnostic
# repeteix aquest PUT amb les mateixes capcaleres i TOTS els ids pendents d'un
# cop, mostra l'estructura del preu i ho prova tambe a una fulla gran.
FULLES = [('ctics', ['llets-i-begudes-vegetals', 'packs']),
          ('per la llar', ['parament-de-la-llar', 'per-cuinar', 'estris-de-cuina'])]

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
fetch(url, {method: 'PUT', credentials: 'include', headers: capcaleres, body: cos})
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
                trobats[o['productId']] = (o['name'], preu, o)
            for v in o.values():
                recorre(v)
        elif isinstance(o, list):
            for v in o:
                recorre(v)
    recorre(dades)
    return trobats


def provar_fulla(scraper, principals, clau, cami):
    d = scraper.driver
    url = next((u for n, u in principals if clau in n), None)
    for slug in cami:
        if not url:
            break
        d.get(url)
        time.sleep(3)
        url = next((u for _, u in scraper.get_subcategories(url) if u.rstrip('/').split('/')[-2] == slug), None)
    print(f"\n{'=' * 90}\nFulla: {url}")
    if not url:
        return
    d.get_log('performance')
    d.get(url)
    time.sleep(5)
    estat = d.execute_script(JS_IDS)
    print(f"Grups: {estat['grups']} | ids {len(estat['ids'])} | totalProducts {estat['total']} | "
          f"amb detall inicial {len(estat['entitats'])}")
    # Un parell de scrolls perque la pagina faci almenys un PUT i en copiem les capcaleres
    for _ in range(6):
        d.execute_script('window.scrollBy(0, 800)')
        time.sleep(0.8)
    time.sleep(2)
    put = None
    for entrada in d.get_log('performance'):
        try:
            msg = json.loads(entrada['message'])['message']
        except Exception:
            continue
        p = msg.get('params', {})
        if msg.get('method') == 'Network.requestWillBeSent' and 'webproductpagews' in p.get('request', {}).get('url', '') \
                and p['request'].get('method') == 'PUT':
            put = put or dict(p['request'], requestId=p['requestId'])
        elif msg.get('method') == 'Network.requestWillBeSentExtraInfo' and put and p.get('requestId') == put['requestId']:
            put['capcaleres_reals'] = p.get('headers', {})
    if not put:
        print("No s'ha capturat cap PUT de la pagina")
        return
    try:
        cos = d.execute_cdp_cmd('Network.getResponseBody', {'requestId': put['requestId']})
        exemple = next(iter(productes_de_resposta(json.loads(cos['body'])).values()), None)
        if exemple:
            print(f"Exemple de producte del PUT (camps de preu i mida):")
            o = exemple[2]
            print(json.dumps({k: o.get(k) for k in o if k in ('name', 'brand', 'price', 'unitPrice', 'size',
                              'packSizeDescription', 'catchWeight', 'promotions', 'available')},
                             ensure_ascii=False)[:1500])
    except Exception as e:
        print(f"Resposta del PUT no disponible: {str(e)[:150]}")

    capcaleres = {k: v for k, v in (put.get('capcaleres_reals') or put.get('headers') or {}).items()
                  if not k.startswith(':') and k.lower() not in ('content-length', 'cookie', 'host', 'accept-encoding',
                                                                 'connection', 'origin', 'referer', 'user-agent',
                                                                 'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site',
                                                                 'priority') and not k.lower().startswith('sec-ch')}
    print(f"Capcaleres copiades: {sorted(capcaleres)}")
    pendents = [i for i in estat['ids'] if i not in estat['entitats']]
    inici = time.time()
    status, mida, text = d.execute_async_script(JS_POST, put['url'], json.dumps(pendents), capcaleres)
    print(f"PUT amb {len(pendents)} ids d'un cop: status={status} mida={mida} ({time.time() - inici:.1f}s)")
    if status == 200:
        trobats = productes_de_resposta(json.loads(text))
        print(f"Productes retornats: {len(trobats)} | + {len(estat['entitats'])} de l'estat inicial = "
              f"{len(trobats) + len(estat['entitats'])} de {estat['total']}")
        for pid, (nom, preu, o) in list(trobats.items())[:5]:
            print(f"   {json.dumps(o.get('price'), ensure_ascii=False)[:160]} | {nom}")
    else:
        print(text[:400])


def main():
    scraper = BonPreuEsclatScraper(categories_filtre=['ctics', 'per la llar'])
    scraper._crear_driver_nou()
    principals = [(n.lower(), u) for n, u in scraper.descobrir_categories()]
    for clau, cami in FULLES:
        try:
            provar_fulla(scraper, principals, clau, cami)
        except Exception as e:
            print(f"❌ {cami}: {str(e)[:300]}")
    try:
        scraper.driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()
