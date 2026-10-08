# debug_bonpreu_api2.py — Script de nomes diagnostic, NO toca Google Sheets ni
# el scraper de produccio.
#
# El primer diagnostic de l'API (debug_bonpreu_api.py, 08/10) va trobar:
#   - window.__INITIAL_STATE__ (734 KB) incrustat a la pagina, amb productId
#   - POST /api/webproductpagews/v6/products: la pagina hi demana els detalls
#     dels productes a mesura que es fa scroll (el GET retorna 405)
# Aquest diagnostic, a la fulla "packs" de llet (21 amb el metode actual, 90 de
# veritat):
#   1. Intercepta les crides fetch de la pagina per veure el cos exacte del POST
#   2. Analitza __INITIAL_STATE__: quants productId hi ha i on, i l'estructura
#      d'un producte (nom, preu, mida)
#   3. Repeteix el POST amb tots els productId de la fulla i compta quants
#      productes retorna amb nom i preu

import ast
import json
import re
import time

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

FULLA = ('ctics', ['llets-i-begudes-vegetals', 'packs'])

JS_INTERCEPTAR = """
window.__peticions = [];
const fetchOriginal = window.fetch;
window.fetch = function(input, init) {
  try {
    const url = (typeof input === 'string') ? input : input.url;
    if (url.includes('/api/')) {
      window.__peticions.push({url: url, method: (init && init.method) || 'GET',
                               body: init && init.body ? String(init.body).slice(0, 3000) : null,
                               headers: init && init.headers ? JSON.stringify(init.headers).slice(0, 1500) : null});
    }
  } catch (e) {}
  return fetchOriginal.apply(this, arguments);
};
"""

JS_ANALITZAR_ESTAT = """
const s = window.__INITIAL_STATE__ || {};
const ids = new Set();
const camins = {};
let exemple = null;
function recorre(o, cami, prof) {
  if (!o || typeof o !== 'object' || prof > 12) return;
  if (Array.isArray(o)) {
    if (o.length && typeof o[0] === 'string' && /^[0-9a-f-]{20,}$/.test(o[0]) && cami.toLowerCase().includes('product')) {
      camins[cami] = o.length;
    }
    o.forEach((v, i) => recorre(v, cami + '[]', prof + 1));
    return;
  }
  for (const k of Object.keys(o)) {
    const v = o[k];
    if (k === 'productId' && typeof v === 'string') ids.add(v);
    if (!exemple && o.productId && (o.name || o.price)) exemple = o;
    recorre(v, cami + '.' + k, prof + 1);
  }
}
recorre(s, 'estat', 0);
return {claus_data: Object.keys(s.data || {}), n_ids: ids.size, ids: Array.from(ids),
        camins: camins, exemple: exemple ? JSON.stringify(exemple).slice(0, 2500) : null};
"""

JS_POST = """
const [url, cos, capçaleres] = [arguments[0], arguments[1], arguments[2]];
const done = arguments[arguments.length - 1];
fetch(url, {method: 'POST', credentials: 'include', headers: capçaleres, body: cos})
  .then(r => r.text().then(t => done([r.status, t.length, t])))
  .catch(e => done([0, 0, String(e)]));
"""


def carregar_classe():
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    for node in ast.parse(font).body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            espai = {'SeleniumBaseDriver': SeleniumBaseDriver, 'By': By, 'time': time, 're': re}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


BonPreuEsclatScraper = carregar_classe()


def resum_producte(p):
    # Treu els camps que ens interessen d'un producte de l'API, sigui quina sigui l'estructura
    text = json.dumps(p, ensure_ascii=False)
    return text[:600]


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

    try:
        d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': JS_INTERCEPTAR})
        print("Interceptor de fetch instal·lat via CDP")
    except Exception as e:
        print(f"⚠️  No s'ha pogut instal·lar l'interceptor via CDP: {e}")
    d.get(url)
    time.sleep(5)

    print("\n######## 2. __INITIAL_STATE__ ########")
    estat = d.execute_script(JS_ANALITZAR_ESTAT)
    print(f"Claus de data: {estat['claus_data']}")
    print(f"productId diferents: {estat['n_ids']}")
    print(f"Llistes d'ids de producte: {estat['camins']}")
    print(f"Exemple de producte:\n{estat['exemple']}")

    for _ in range(25):
        d.execute_script('window.scrollBy(0, 600)')
        time.sleep(0.8)

    print("\n######## 1. Crides fetch a /api/ durant l'scroll ########")
    peticions = d.execute_script('return window.__peticions || []')
    post = None
    for p in peticions:
        print(f"  {p['method']} {p['url'][:200]}\n     body: {str(p['body'])[:600]}\n     headers: {p['headers']}")
        if p['method'] == 'POST' and 'webproductpagews' in p['url'] and not post:
            post = p

    print("\n######## 3. POST amb tots els productId de la fulla ########")
    ids = estat['ids']
    if not post:
        print("No s'ha vist cap POST de productes; es prova el format habitual")
        post = {'url': '/api/webproductpagews/v6/products', 'body': None, 'headers': None}
    capcaleres = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    try:
        capcaleres.update(json.loads(post['headers'] or '{}'))
    except Exception:
        pass
    cossos = []
    if post['body']:
        try:
            original = json.loads(post['body'])
            clau = next((k for k, v in original.items() if isinstance(v, list)), None)
            if clau:
                original[clau] = ids
                cossos.append(json.dumps(original))
        except Exception:
            pass
    cossos += [json.dumps({'productIds': ids}), json.dumps(ids)]
    for cos in cossos:
        status, mida, text = d.execute_async_script(JS_POST, post['url'], cos, capcaleres)
        print(f"\n  cos={cos[:150]}...\n  status={status} mida={mida}")
        if status == 200:
            try:
                dades = json.loads(text)
            except Exception:
                print(f"  (no es JSON) {text[:500]}")
                continue
            llista = dades if isinstance(dades, list) else next(
                (v for v in dades.values() if isinstance(v, list)), [])
            print(f"  claus: {list(dades)[:15] if isinstance(dades, dict) else 'llista'} | productes retornats: {len(llista)}")
            for p in llista[:3]:
                print(f"   - {resum_producte(p)}")
            break
        else:
            print(f"  {text[:400]}")

    try:
        d.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()
