# debug_bonpreu_api_escala.py — Script de nomes diagnostic, NO toca Google
# Sheets ni el scraper de produccio.
#
# debug_bonpreu_api4.py (08/10) va confirmar que, a cada fulla, l'estat inicial
# de la pagina (window.__INITIAL_STATE__) te tots els ids i el detall dels
# primers 30, i que un sol PUT /api/webproductpagews/v6/products amb la resta
# d'ids (copiant les capcaleres de la pagina) dona tots els productes:
# 90/90 a packs de llet i 300/300 a estris de cuina.
#
# Aquest diagnostic prova el metode a escala, amb tota la categoria
# "Làctics i ous":
#   1. La pagina de la categoria principal: quants ids te (si ja els dona tots,
#      no caldria recorrer les fulles)
#   2. Recorregut de totes les fulles amb el metode nou: total de productes,
#      temps, si les capcaleres es poden reutilitzar entre fulles, i si la
#      sessio es degrada
#   3. Comparacio amb el metode actual (Part 4 del 07/10: llet-sencera 7,
#      packs 21...) i exemples de productes amb tots els camps

import ast
import functools
import json
import re
import time

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

CATEGORIA = 'ctics'   # "Làctics i ous"

JS_ESTAT = """
const s = window.__INITIAL_STATE__ || {};
const prods = ((s.data || {}).products || {});
const cat = ((prods.catalogue || {}).data) || {};
const ids = [];
(cat.productGroups || []).forEach(g => (g.products || []).forEach(id => { if (id && !ids.includes(id)) ids.push(id); }));
return {ids: ids, total: cat.totalProducts || null, entitats: prods.productEntities || {}};
"""

JS_PUT = """
const [url, cos, capcaleres] = [arguments[0], arguments[1], arguments[2]];
const done = arguments[arguments.length - 1];
fetch(url, {method: 'PUT', credentials: 'include', headers: capcaleres, body: cos})
  .then(r => r.text().then(t => done([r.status, t])))
  .catch(e => done([0, String(e)]));
"""

URL_PUT = 'https://www.compraonline.bonpreuesclat.cat/api/webproductpagews/v6/products'
EXCLOSES = ('content-length', 'cookie', 'host', 'accept-encoding', 'connection', 'origin', 'referer',
            'user-agent', 'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site', 'priority')


def carregar_classe():
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    for node in ast.parse(font).body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            espai = {'SeleniumBaseDriver': functools.partial(SeleniumBaseDriver, log_cdp=True),
                     'By': By, 'time': time, 're': re}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


BonPreuEsclatScraper = carregar_classe()


def normalitzar(o):
    # Treu els camps utils d'un producte, tant de l'estat inicial com del PUT
    preu = o.get('price') or {}
    import_preu = (preu.get('current') or {}).get('amount') or preu.get('amount')
    unitari = o.get('unitPrice') or {}
    preu_unitat = (unitari.get('price') or {}).get('amount') or ((preu.get('unit') or {}).get('current') or {}).get('amount')
    unitat = unitari.get('unitName') or (preu.get('unit') or {}).get('label')
    return {'nom': o.get('name'), 'marca': o.get('brand'), 'preu': import_preu,
            'format': o.get('packSizeDescription') or o.get('size'), 'preu_unitat': preu_unitat,
            'unitat': unitat, 'disponible': o.get('available')}


def productes_de(dades):
    trobats = {}

    def recorre(x):
        if isinstance(x, dict):
            if x.get('productId') and x.get('name'):
                trobats[x['productId']] = normalitzar(x)
            for v in x.values():
                recorre(v)
        elif isinstance(x, list):
            for v in x:
                recorre(v)
    recorre(dades)
    return trobats


class Prova:
    def __init__(self):
        self.scraper = BonPreuEsclatScraper(categories_filtre=[CATEGORIA])
        self.scraper._crear_driver_nou()
        self.capcaleres = None
        self.captures = 0
        self.reutilitzades = 0

    @property
    def d(self):
        return self.scraper.driver

    def capturar_capcaleres(self):
        # Fa uns scrolls perque la pagina faci un PUT i en copia les capcaleres
        self.d.get_log('performance')
        for _ in range(5):
            self.d.execute_script('window.scrollBy(0, 800)')
            time.sleep(0.7)
        time.sleep(1.5)
        put = None
        for entrada in self.d.get_log('performance'):
            try:
                msg = json.loads(entrada['message'])['message']
            except Exception:
                continue
            p = msg.get('params', {})
            if msg.get('method') == 'Network.requestWillBeSent' and 'webproductpagews' in p.get('request', {}).get('url', '') \
                    and p['request'].get('method') == 'PUT':
                put = put or {'id': p['requestId'], 'h': p['request'].get('headers', {})}
            elif msg.get('method') == 'Network.requestWillBeSentExtraInfo' and put and p.get('requestId') == put['id']:
                put['h'] = p.get('headers', put['h'])
        if put:
            self.capcaleres = {k: v for k, v in put['h'].items()
                               if not k.startswith(':') and k.lower() not in EXCLOSES and not k.lower().startswith('sec-ch')}
            self.captures += 1
        return bool(put)

    def llegir_fulla(self, url):
        self.d.get(url)
        time.sleep(4)
        estat = self.d.execute_script(JS_ESTAT)
        productes = productes_de(estat['entitats'])
        pendents = [i for i in estat['ids'] if i not in productes]
        if pendents:
            if not self.capcaleres and not self.capturar_capcaleres():
                return estat, productes, 'sense capcaleres'
            status, text = self.d.execute_async_script(JS_PUT, URL_PUT, json.dumps(pendents), self.capcaleres)
            if status != 200:
                # Les capcaleres d'una altra pagina no serveixen: es tornen a capturar
                if self.capturar_capcaleres():
                    status, text = self.d.execute_async_script(JS_PUT, URL_PUT, json.dumps(pendents), self.capcaleres)
            else:
                self.reutilitzades += 1
            if status == 200:
                productes.update(productes_de(json.loads(text)))
            else:
                return estat, productes, f'PUT {status}'
        return estat, productes, 'ok'


def main():
    prova = Prova()
    sc = prova.scraper
    principals = [(n, u) for n, u in sc.descobrir_categories()]
    nom_cat, url_cat = next((n, u) for n, u in principals if CATEGORIA in n.lower())
    inici = time.time()

    print(f"\n######## 1. Pagina de la categoria principal: {nom_cat} ########")
    estat, productes, resultat = prova.llegir_fulla(url_cat)
    print(f"ids {len(estat['ids'])} | totalProducts {estat['total']} | productes amb detall {len(productes)} ({resultat})")
    ids_principal = set(estat['ids'])

    print("\n######## 2. Totes les fulles amb el metode nou ########")
    tots = {}
    fulles = []
    pila = [(url_cat, 0)]
    while pila:
        url, nivell = pila.pop(0)
        sc.driver.get(url)
        time.sleep(3)
        subcats = sc.get_subcategories(url)
        if subcats:
            pila = [(u, nivell + 1) for _, u in subcats] + pila
            continue
        t = time.time()
        estat, productes, resultat = prova.llegir_fulla(url)
        nom = url.rstrip('/').split('/')[-2]
        if not estat['ids']:
            print(f"   ⚠️  {nom}: 0 ids, reiniciant navegador...")
            sc._crear_driver_nou()
            prova.capcaleres = None
            estat, productes, resultat = prova.llegir_fulla(url)
        tots.update(productes)
        fulles.append((nom, len(estat['ids']), estat['total'], len(productes)))
        print(f"   {nom:<45} ids {len(estat['ids']):>4} total {str(estat['total']):>4} "
              f"amb detall {len(productes):>4} ({resultat}, {time.time() - t:.1f}s)")

    minuts = (time.time() - inici) / 60
    print(f"\n######## Resum ########")
    print(f"Fulles: {len(fulles)} | productes diferents: {len(tots)} | temps {minuts:.1f} min | "
          f"reinicis {sc.reinicis - 1} | capcaleres capturades {prova.captures}, reutilitzades {prova.reutilitzades}")
    print(f"Fulles incompletes (detall < ids): {[f for f in fulles if f[3] < f[1]]}")
    print(f"Ids de la pagina principal: {len(ids_principal)} | coincideixen amb les fulles: "
          f"{len(ids_principal & set(tots))}")
    print("Metode actual a la Part 4 del 28/09 per a aquesta categoria: 440 productes")
    print("\nExemples:")
    for p in list(tots.values())[:: max(1, len(tots) // 15)][:15]:
        print(f"   {p['preu']:>6} € | {str(p['format']):<12} | {p['preu_unitat']} {p['unitat']} | "
              f"{p['marca']} | {p['nom']}")
    sense_preu = [p for p in tots.values() if not p['preu']]
    print(f"\nProductes sense preu: {len(sense_preu)} | sense format: "
          f"{sum(1 for p in tots.values() if not p['format'])} | no disponibles: "
          f"{sum(1 for p in tots.values() if p['disponible'] is False)}")
    try:
        sc.driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()
