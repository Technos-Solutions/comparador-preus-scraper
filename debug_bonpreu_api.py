# debug_bonpreu_api.py — Script de nomes diagnostic, NO toca Google Sheets ni
# el scraper de produccio.
#
# El diagnostic del 08/10 (debug_bonpreu_llista_virtual.py) va mostrar que el
# scraper de Bon Preu nomes llegeix els primers productes de cada fulla (llista
# virtual): a "packs" de llet en llegeix 21 i n'hi ha 90; a "estris de cuina",
# 21 de mes de 245. Llegir durant l'scroll es massa lent per al limit de 6 h.
# Seguint la metodologia (buscar l'API interna del lloc abans que res mes),
# aquest diagnostic:
#   1. Obre una fulla, fa scroll i registra totes les peticions de dades que
#      fa la pagina (fetch / XMLHttpRequest), amb la mida de la resposta
#   2. Torna a demanar, des de la mateixa pagina (mateixes cookies), les que
#      semblen d'API i mostra el tipus, la mida i l'inici de la resposta
#   3. Busca dades de productes incrustades a l'HTML (JSON en etiquetes script)

import ast
import json
import re
import time

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

FULLA = ('ctics', ['llets-i-begudes-vegetals', 'packs'])   # 21 amb el metode actual, 90 de veritat


def carregar_classe():
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    for node in ast.parse(font).body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            espai = {'SeleniumBaseDriver': SeleniumBaseDriver, 'By': By, 'time': time, 're': re}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


BonPreuEsclatScraper = carregar_classe()

JS_PETICIONS = """
return performance.getEntriesByType('resource')
  .filter(e => e.initiatorType === 'fetch' || e.initiatorType === 'xmlhttprequest')
  .map(e => [e.name, e.initiatorType, e.transferSize || 0, Math.round(e.duration)]);
"""

JS_FETCH = """
const url = arguments[0];
const done = arguments[arguments.length - 1];
fetch(url, {credentials: 'include', headers: {'Accept': 'application/json, text/plain, */*'}})
  .then(r => r.text().then(t => done([r.status, r.headers.get('content-type') || '', t.length, t.slice(0, 1500)])))
  .catch(e => done([0, 'error', 0, String(e)]));
"""


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

    d.get(url)
    time.sleep(5)
    for _ in range(25):
        d.execute_script('window.scrollBy(0, 600)')
        time.sleep(0.8)
    time.sleep(2)

    print("\n######## 1. Peticions de dades de la pagina ########")
    peticions = d.execute_script(JS_PETICIONS)
    vistes = []
    for nom, tipus, mida, ms in peticions:
        base = nom.split('?')[0]
        print(f"  {tipus:<15} {mida:>8} B {ms:>5} ms  {nom[:400]}")
        vistes.append(nom)

    print("\n######## 2. Respostes de les peticions candidates ########")
    candidates = []
    for nom in vistes:
        if any(k in nom.lower() for k in ('api', 'product', 'categor', 'search', 'graphql', 'browse')) \
                and nom not in candidates:
            candidates.append(nom)
    for nom in candidates[:15]:
        try:
            status, ctype, mida, inici = d.execute_async_script(JS_FETCH, nom)
        except Exception as e:
            print(f"\n▶ {nom[:300]}\n   ❌ {e}")
            continue
        print(f"\n▶ {nom[:300]}\n   status={status} tipus={ctype} mida={mida}")
        print(f"   {inici[:1500]}")
        if 'json' in ctype:
            try:
                dades = json.loads(inici) if mida <= 1500 else None
            except Exception:
                dades = None
            if dades is not None:
                print(f"   claus: {list(dades)[:20] if isinstance(dades, dict) else type(dades).__name__}")

    print("\n######## 3. Dades incrustades a l'HTML ########")
    scripts = d.execute_script("""
        return Array.from(document.querySelectorAll('script'))
          .map(s => [s.id || '', s.type || '', (s.textContent || '').length,
                     (s.textContent || '').includes('productId') || (s.textContent || '').includes('"retailerProductId"'),
                     (s.textContent || '').slice(0, 200)])
          .filter(s => s[2] > 500);
    """)
    for sid, stype, mida, te_productes, inici in scripts:
        print(f"  id={sid!r} type={stype!r} mida={mida} productes={te_productes} | {inici[:200]!r}")

    try:
        d.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()
