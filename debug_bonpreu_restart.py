# debug_bonpreu_restart.py — Script de només diagnòstic, NO toca cap
# dada ni el scraper de producció. El test complet anterior
# (debug_bonpreu_full_test.py) va confirmar que Chrome real (headed) +
# Xvfb evita la pantalla "Human Verification", pero va detectar un
# problema nou: despres d'uns 15-20 minuts de sessio continua del
# mateix navegador, TOTES les subcategories restants van donar 0
# productes de cop (incloent categories que no poden estar buides de
# veritat, com "carnisseria"), fins i tot la categoria seguent
# (Begudes). Sembla degradacio de sessio / limitacio per activitat
# continuada, no deteccio de bot.
#
# Aquest script prova la solucio mes simple: reiniciar el navegador
# (tancar-lo i tornar a obrir amb SeleniumBase, refent cookie i idioma)
# cada cert temps, en lloc de mantenir una unica sessio llarga. Es
# torna a provar sobre les mateixes 2 categories principals (Frescos +
# Begudes) per veure si aixo soluciona la degradacio detectada.

import time
from seleniumbase import Driver

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'
CATEGORIES_A_PROVAR = ['frescos', 'begudes']

# Reiniciem el navegador si ha passat mes d'aquest temps des de l'ultim
# reinici, comprovat abans de processar cada categoria/subcategoria.
MAX_MINUTS_SESSIO = 8


class GestorDriver:
    def __init__(self):
        self.driver = None
        self.inici_sessio = 0
        self.reinicis = 0
        self._crear_nou()

    def _crear_nou(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.reinicis += 1
        print(f"🔄 (Re)iniciant navegador (reinici #{self.reinicis}) ...")
        self.driver = Driver(uc=True, headed=True)
        self.driver.uc_open_with_reconnect(BASE_URL, reconnect_time=6)
        time.sleep(3)
        self.driver.add_cookie({
            "name": "language",
            "value": "ca",
            "domain": "www.compraonline.bonpreuesclat.cat"
        })
        self.driver.refresh()
        time.sleep(5)
        self.inici_sessio = time.time()

    def reiniciar_si_cal(self):
        minuts_actius = (time.time() - self.inici_sessio) / 60
        if minuts_actius >= MAX_MINUTS_SESSIO:
            print(f"⏱️  Sessio activa {minuts_actius:.1f} min (>= {MAX_MINUTS_SESSIO}), reiniciant navegador...")
            self._crear_nou()

    def quit(self):
        try:
            self.driver.quit()
        except Exception:
            pass


def get_subcategories(driver, url):
    path_pare = url.split('/categories/')[-1].split('?')[0]
    segments_pare = [s for s in path_pare.split('/') if s]
    slug_pare = segments_pare[0]
    n_segments_pare = len(segments_pare)

    links = driver.find_elements('a[href*="/categories/"]')
    subcats = []
    uuids_vistos = set()
    for link in links:
        try:
            href = link.get_attribute('href') or ''
            text = link.get_attribute('innerText').strip()
        except Exception:
            continue
        if '/categories/' not in href or not text:
            continue
        path = href.split('/categories/')[-1].split('?')[0]
        segments = [s for s in path.split('/') if s]
        uuid = segments[-1] if segments else ''
        if (len(segments) == n_segments_pare + 1
                and segments[0] == slug_pare
                and len(uuid) > 10
                and uuid not in uuids_vistos):
            uuids_vistos.add(uuid)
            url_neta = f"{BASE_URL}/categories/{path}"
            subcats.append((text, url_neta))
    return subcats


def extreure_productes_pagina(driver, url):
    productes = []
    try:
        driver.get(url)
        time.sleep(4)
        anterior = 0
        for i in range(8):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1.5)
            actual = len(driver.find_elements('h3[data-test="fop-title"]'))
            if actual == anterior and i > 1:
                break
            anterior = actual

        noms = driver.find_elements('h3[data-test="fop-title"]')
        preus = driver.find_elements('span[data-test="fop-price"]')
        for i in range(min(len(noms), len(preus))):
            try:
                nom = noms[i].text.strip()
                preu_text = preus[i].text.strip()
                preu_text = preu_text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                preu = float(preu_text)
                if nom and preu > 0:
                    productes.append((nom, preu))
            except Exception:
                continue
    except Exception as e:
        print(f"      ❌ Error extraient: {e}")
    return productes


def scrape_recursiu(gestor, url, nivell=0, totals=None):
    if totals is None:
        totals = []
    prefix = '  ' * (nivell + 2)
    gestor.reiniciar_si_cal()
    driver = gestor.driver
    try:
        driver.get(url)
        time.sleep(3)
        subcats = get_subcategories(driver, url)
        nom_cat = url.split('/')[-2]

        if subcats:
            print(f"{prefix}📂 {nom_cat}: {len(subcats)} subcategories")
            for nom_sub, url_sub in subcats:
                scrape_recursiu(gestor, url_sub, nivell + 1, totals)
        else:
            productes = extreure_productes_pagina(gestor.driver, url)
            print(f"{prefix}└ {nom_cat}: {len(productes)} productes")
            if productes:
                print(f"{prefix}   Exemple: {productes[0]}")
            totals.append((nom_cat, len(productes)))
    except Exception as e:
        nom_cat = url.split('/')[-2]
        print(f"{prefix}❌ Error {nom_cat}: {e}")
    return totals


def main():
    gestor = GestorDriver()
    try:
        driver = gestor.driver
        links = driver.find_elements('a[href*="/categories/"]')
        categories = []
        uuids_vistos = set()
        for link in links:
            href = link.get_attribute('href')
            text = link.get_attribute('innerText').strip().lower()
            if not href or not text:
                continue
            uuid = href.split('/')[-1].split('?')[0]
            if uuid in uuids_vistos:
                continue
            if any(cat in text for cat in CATEGORIES_A_PROVAR):
                uuids_vistos.add(uuid)
                url_neta = f"{BASE_URL}/categories/{href.split('/categories/')[1].split('?')[0]}"
                categories.append((text.title(), url_neta))

        print(f"\n✅ Categories principals trobades: {categories}\n")

        gran_total = 0
        for nom_cat, url_cat in categories:
            print(f"📂 Categoria principal: {nom_cat}")
            totals = scrape_recursiu(gestor, url_cat, nivell=0)
            subtotal = sum(n for _, n in totals)
            gran_total += subtotal
            zeros = [n for n, c in totals if c == 0]
            print(f"  ✅ Total {nom_cat}: {subtotal} productes ({len(totals)} subcategories finals, {len(zeros)} a 0)\n")

        print(f"\n🏁 GRAN TOTAL ({', '.join(CATEGORIES_A_PROVAR)}): {gran_total} productes")
        print(f"🔄 Reinicis de navegador fets: {gestor.reinicis}")

    finally:
        gestor.quit()


if __name__ == '__main__':
    main()
