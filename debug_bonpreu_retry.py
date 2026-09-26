# debug_bonpreu_retry.py — Script de només diagnòstic, NO toca cap dada
# ni el scraper de producció. El reinici per temps fix (cada 8 minuts,
# debug_bonpreu_restart.py) no ha estat prou fiable: la degradacio de
# sessio no segueix un rellotge exacte (carnisseria va encadenar 10
# subcategories a 0 abans dels 8 minuts) i Begudes ha seguit sempre a 0.
#
# Aquest script canvia d'estrategia: en lloc de reiniciar per temps,
# reacciona al simptoma real. Si una subcategoria dona 0 productes,
# es reintenta un cop (nomes recarregant la pagina). Si dues seguides
# donen 0, es reinicia tot el navegador (tanca i torna a obrir amb
# SeleniumBase, refent cookie d'idioma) i es reintenta la subcategoria
# actual abans de continuar. Aixo hauria de detectar i corregir la
# degradacio just quan passa, en lloc d'endevinar un temps fix.

import time
from seleniumbase import Driver

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'
CATEGORIES_A_PROVAR = ['frescos', 'begudes']
ZEROS_SEGUITS_PER_REINICI = 2


class GestorDriver:
    def __init__(self):
        self.driver = None
        self.reinicis = 0
        self.zeros_seguits = 0
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

    def marcar_resultat(self, n_productes):
        if n_productes == 0:
            self.zeros_seguits += 1
        else:
            self.zeros_seguits = 0

    def cal_reiniciar(self):
        return self.zeros_seguits >= ZEROS_SEGUITS_PER_REINICI

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


def get_subcategories_amb_reintent(gestor, url, prefix):
    """Com get_subcategories, pero si dona 0 i el gestor ja porta zeros
    seguits, reinicia i reintenta un cop abans d'acceptar que no n'hi ha."""
    subcats = get_subcategories(gestor.driver, url)
    if not subcats and gestor.zeros_seguits + 1 >= ZEROS_SEGUITS_PER_REINICI:
        print(f"{prefix}⚠️  0 subcategories i ja portava zeros seguits, reiniciant per comprovar...")
        gestor._crear_nou()
        gestor.zeros_seguits = 0
        gestor.driver.get(url)
        time.sleep(3)
        subcats = get_subcategories(gestor.driver, url)
    return subcats


def extreure_amb_reintent(gestor, url, prefix):
    productes = extreure_productes_pagina(gestor.driver, url)
    if not productes:
        gestor.zeros_seguits += 1
        if gestor.cal_reiniciar():
            print(f"{prefix}⚠️  {gestor.zeros_seguits} subcategories seguides a 0, reiniciant navegador i reintentant...")
            gestor._crear_nou()
            gestor.zeros_seguits = 0
            productes = extreure_productes_pagina(gestor.driver, url)
            print(f"{prefix}   Despres del reinici: {len(productes)} productes")
    gestor.marcar_resultat(len(productes))
    return productes


def scrape_recursiu(gestor, url, nivell=0, totals=None):
    if totals is None:
        totals = []
    prefix = '  ' * (nivell + 2)
    try:
        gestor.driver.get(url)
        time.sleep(3)
        subcats = get_subcategories_amb_reintent(gestor, url, prefix)
        nom_cat = url.split('/')[-2]

        if subcats:
            print(f"{prefix}📂 {nom_cat}: {len(subcats)} subcategories")
            gestor.zeros_seguits = 0
            for nom_sub, url_sub in subcats:
                scrape_recursiu(gestor, url_sub, nivell + 1, totals)
        else:
            productes = extreure_amb_reintent(gestor, url, prefix)
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
            gestor.zeros_seguits = 0
            totals = scrape_recursiu(gestor, url_cat, nivell=0)
            subtotal = sum(n for _, n in totals)
            gran_total += subtotal
            zeros = [n for n, c in totals if c == 0]
            print(f"  ✅ Total {nom_cat}: {subtotal} productes ({len(totals)} subcategories finals, {len(zeros)} a 0: {zeros})\n")

        print(f"\n🏁 GRAN TOTAL ({', '.join(CATEGORIES_A_PROVAR)}): {gran_total} productes")
        print(f"🔄 Reinicis de navegador fets: {gestor.reinicis}")

    finally:
        gestor.quit()


if __name__ == '__main__':
    main()
