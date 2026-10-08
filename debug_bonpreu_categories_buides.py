# debug_bonpreu_categories_buides.py — Script de nomes diagnostic, NO toca
# Google Sheets ni el scraper de produccio.
#
# Context (Part 4 del 07/10): Neteja de la llar, Per la llar, Espai Mascotes,
# Nadons i Parafarmacia van sortir a 0 sense cap reinici del navegador. Causa
# probable: la sessio es va degradar just en comencar "Neteja de la llar", i
# scrape_all() posa zeros_seguits a 0 a cada categoria principal; com que cada
# categoria principal nomes aportava UN zero, mai s'arribava als 2 seguits que
# activen el reinici. El 28/09 la mateixa categoria tenia 10 subcategories.
#
# Aquest diagnostic comprova dues coses:
#   1. Amb un navegador nou, les 5 categories tenen subcategories i productes
#      (es a dir, no han desaparegut de la web), aplicant la correccio
#      proposada: si una categoria principal acaba amb 0 productes, reiniciar
#      el navegador i tornar-la a recorrer un cop.
#   2. Si les fulles de 21 productes (33 al run del 28/09) son un limit de la
#      pagina: es fa mes scroll, es busca un boto de "mes productes" i el
#      recompte que mostri la web.
#
# Fa servir la mateixa classe BonPreuEsclatScraper de scraper_main.py (llegida
# del fitxer, sense importar-lo, perque en importar-lo es connecta a Sheets).

import ast
import re
import time

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

CATEGORIES = ['neteja', 'per la llar', 'mascotes', 'nadons', 'parafarm']
# Fulles que el 28/09 van donar exactament 21 productes (cami des de la
# categoria principal, per slug)
FULLES_21 = [
    ('ctics', ['llets-i-begudes-vegetals', 'packs']),
    ('cura', ['cosm%C3%A8tica-facial', 'maquillatge', 'llavis']),
    ('cura', ['cosm%C3%A8tica-facial', 'cura-facial', 'hidratants-i-nutritives']),
]


def carregar_classe():
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    arbre = ast.parse(font)
    for node in arbre.body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            espai = {'SeleniumBaseDriver': SeleniumBaseDriver, 'By': By, 'time': time, 're': re}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


BonPreuEsclatScraper = carregar_classe()


class BonPreuCorregit(BonPreuEsclatScraper):
    def scrape_all(self):
        # Igual que a produccio, pero si una categoria principal acaba amb 0
        # productes, es reinicia el navegador i es torna a recorrer un cop
        self._crear_driver_nou()
        categories = self.descobrir_categories()
        resum = []
        for nom_cat, url_cat in categories:
            print(f"  📂 Categoria principal: {nom_cat}")
            abans = len(self.productes)
            self.zeros_seguits = 0
            self.scrape_recursiu(url_cat, nivell=0)
            if len(self.productes) == abans:
                print(f"  ⚠️  {nom_cat}: 0 productes, reiniciant navegador i reintentant la categoria...")
                self._crear_driver_nou()
                self.zeros_seguits = 0
                self.scrape_recursiu(url_cat, nivell=0)
            resum.append((nom_cat, len(self.productes) - abans))
            time.sleep(2)
        return resum


def provar_categories():
    print("\n######## 1. Categories que van sortir a 0 el 07/10 ########")
    scraper = BonPreuCorregit(categories_filtre=CATEGORIES)
    inici = time.time()
    try:
        resum = scraper.scrape_all()
    finally:
        try:
            scraper.driver.quit()
        except Exception:
            pass
    print(f"\nResum ({(time.time() - inici) / 60:.0f} min, reinicis {scraper.reinicis}):")
    for nom, n in resum:
        print(f"   {nom:<25} {n:>5} productes")
    print(f"   TOTAL {len(scraper.productes)} (el 28/09 aquestes categories formaven part dels 4.183 de la Part 4)")
    print("Exemples:")
    for p in scraper.productes[:: max(1, len(scraper.productes) // 12)][:12]:
        print(f"   {p['preu']:>6} € | {p['quantitat']:<8} | {p['producte']}")


def provar_fulles_21():
    print("\n######## 2. Fulles de 21 productes: limit de la pagina? ########")
    scraper = BonPreuEsclatScraper(categories_filtre=['ctics', 'cura'])
    scraper._crear_driver_nou()
    d = scraper.driver
    try:
        principals = dict((n.lower(), u) for n, u in scraper.descobrir_categories())
        for clau, cami in FULLES_21:
            url = next((u for n, u in principals.items() if clau in n), None)
            for slug in cami:
                if not url:
                    break
                d.get(url)
                time.sleep(3)
                url = next((u for _, u in scraper.get_subcategories(url) if u.rstrip('/').split('/')[-2] == slug), None)
            if not url:
                print(f"   ❌ No trobo la fulla {cami}")
                continue
            d.get(url)
            time.sleep(4)
            recomptes = []
            for _ in range(20):
                d.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(1.5)
                recomptes.append(len(d.find_elements('h3[data-test="fop-title"]')))
            botons = [b.get_attribute('innerText').strip() for b in d.find_elements('button')
                      if any(m in (b.get_attribute('innerText') or '').lower()
                             for m in ('més', 'mes ', 'carrega', 'veure', 'load', 'more', 'següent'))]
            text = d.find_element('body').get_attribute('innerText')
            linies_recompte = [l.strip() for l in text.split('\n')
                               if 'producte' in l.lower() and any(c.isdigit() for c in l)][:5]
            print(f"\n   ▶ {'/'.join(cami)}")
            print(f"     productes visibles durant 20 scrolls: {recomptes}")
            print(f"     botons de 'mes': {botons[:5]}")
            print(f"     linies amb recompte: {linies_recompte}")
    finally:
        try:
            d.quit()
        except Exception:
            pass


if __name__ == '__main__':
    provar_fulles_21()
    provar_categories()
