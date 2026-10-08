# debug_bonpreu_llista_virtual.py — Script de nomes diagnostic, NO toca Google
# Sheets ni el scraper de produccio.
#
# El diagnostic del 08/10 (debug_bonpreu_categories_buides.py) va mostrar que
# a les fulles on el scraper troba exactament 21 productes, la pagina en te 21
# al principi i, en continuar fent scroll, el recompte BAIXA a 9-11: la web fa
# servir una llista virtual (nomes mante al DOM els productes que es veuen).
# El scraper de produccio fa 2-3 scrolls, veu el recompte estable a 21 i llegeix
# aquests 21: els que hi ha mes avall no els veu mai.
#
# Aquest diagnostic compara, a cada fulla de prova:
#   A) el metode actual (extreure_productes_pagina de scraper_main.py)
#   B) un metode nou: baixar a poc a poc i anar llegint els productes visibles
#      a cada pas, sense repetits, fins al final de la pagina
# a 8 fulles que donaven 21 i a 3 fulles petites (per veure que aquestes ja
# eren completes).

import ast
import re
import time

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

FULLES = [
    # (categoria principal, cami de slugs) — les 8 primeres donaven 21
    ('ctics', ['llets-i-begudes-vegetals', 'packs']),
    ('cura', ['cosm%C3%A8tica-facial', 'maquillatge', 'llavis']),
    ('cura', ['cura-de-mans-i-peus', 'manicura-i-pedicura']),
    ('neteja', ['conservaci%C3%B3-d-aliments', 'herm%C3%A8tics-i-ampolles']),
    ('per la llar', ['parament-de-la-llar', 'per-cuinar', 'estris-de-cuina']),
    ('per la llar', ['jocs-i-joguines', 'vehicles']),
    ('per la llar', ['aire-lliure', 'piscina']),
    ('parafarm', ['cura-facial', 'hidrataci%C3%B3-facial']),
    # fulles petites, de control
    ('ctics', ['llets-i-begudes-vegetals', 'llet-sencera']),
    ('congelats', ['verdures-i-hortalisses', 'patates']),
    ('cura', ['cura-del-cabell', 'xamp%C3%BAs-i-tractaments-capil-lars', 'xamp%C3%BA-cabells-normals']),
]


def carregar_classe():
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    for node in ast.parse(font).body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            espai = {'SeleniumBaseDriver': SeleniumBaseDriver, 'By': By, 'time': time, 're': re}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


BonPreuEsclatScraper = carregar_classe()


def llegir_visibles(d):
    # Retorna [(nom, preu)] dels productes que ara mateix son al DOM
    files = []
    noms = d.find_elements('h3[data-test="fop-title"]')
    preus = d.find_elements('span[data-test="fop-price"]')
    for i in range(min(len(noms), len(preus))):
        try:
            files.append((noms[i].get_attribute('innerText').strip(),
                          preus[i].get_attribute('innerText').strip()))
        except Exception:
            continue
    return files


def metode_incremental(d, url, pas=500, max_passos=200):
    d.get(url)
    time.sleep(4)
    vistos = {}
    sense_nous = 0
    passos = 0
    for passos in range(max_passos):
        nous = 0
        for nom, preu in llegir_visibles(d):
            if nom and nom not in vistos:
                vistos[nom] = preu
                nous += 1
        al_final = d.execute_script(
            'return window.scrollY + window.innerHeight >= document.body.scrollHeight - 5')
        sense_nous = 0 if nous else sense_nous + 1
        if al_final and sense_nous >= 3:
            break
        d.execute_script(f'window.scrollBy(0, {pas})')
        time.sleep(0.8)
    return vistos, passos + 1


def main():
    scraper = BonPreuEsclatScraper(categories_filtre=['ctics', 'cura', 'neteja', 'per la llar',
                                                      'parafarm', 'congelats'])
    scraper._crear_driver_nou()
    d = scraper.driver
    principals = [(n.lower(), u) for n, u in scraper.descobrir_categories()]
    resum = []
    for clau, cami in FULLES:
        url = next((u for n, u in principals if clau in n), None)
        for slug in cami:
            if not url:
                break
            d.get(url)
            time.sleep(3)
            url = next((u for _, u in scraper.get_subcategories(url)
                        if u.rstrip('/').split('/')[-2] == slug), None)
        if not url:
            print(f"\n❌ No trobo la fulla {cami}")
            continue

        abans = len(scraper.productes)
        n_actual = scraper.extreure_productes_pagina(url)
        noms_actual = {p['producte'] for p in scraper.productes[abans:]}
        vistos, passos = metode_incremental(d, url)
        nous = [n for n in vistos if n not in noms_actual]
        print(f"\n▶ {'/'.join(cami)}")
        print(f"   A) metode actual: {n_actual} | B) incremental: {len(vistos)} ({passos} passos)")
        for n in nous[:6]:
            print(f"      + {vistos[n]:>8} | {n}")
        resum.append(('/'.join(cami[-2:]), n_actual, len(vistos)))
        if n_actual == 0 and len(vistos) == 0:
            print("   ⚠️  0 i 0: reinicio el navegador")
            scraper._crear_driver_nou()
            d = scraper.driver

    print("\n######## Resum ########")
    for nom, a, b in resum:
        print(f"   {nom:<55} actual {a:>4} | incremental {b:>4} | {'+' + str(b - a) if b > a else '='}")
    try:
        d.quit()
    except Exception:
        pass


if __name__ == '__main__':
    main()
