# debug_bonpreu_full_test.py — Script de només diagnòstic, NO toca cap
# dada ni el scraper de producció. El diagnostic anterior (debug_bonpreu_
# headed.py) va confirmar amb una sola pagina que Chrome real (headed) +
# Xvfb via SeleniumBase evita la pantalla "Human Verification" que
# bloquejava el mode headless. Aquest script fa la prova completa: repeteix
# exactament la mateixa logica recursiva que BonPreuEsclatScraper
# (descobriment de categories + subcategories + extraccio amb scroll fins
# que el compte s'estabilitza) pero amb el driver headed, sobre un parell
# de categories principals senceres, per confirmar que funciona a escala
# real (no nomes 19 productes d'una carrega parcial) abans de tocar
# scraper_main.py.

import time
from seleniumbase import Driver

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'

# Nomes provem 2 categories principals senceres (no les 11) per mantenir
# el temps d'execucio raonable; si aquestes funcionen be, el patro es
# aplicable a la resta.
CATEGORIES_A_PROVAR = ['frescos', 'begudes']


def convertir_pes(pes_text):
    import re
    match = re.match(r'([0-9.]+)(kg|l|g|ml)', pes_text.strip(), re.IGNORECASE)
    if not match:
        return pes_text
    val = float(match.group(1))
    unitat = match.group(2).lower()
    if unitat == 'kg':
        if val < 1:
            return str(int(val * 1000)) + ' g'
        v = int(val) if val == int(val) else val
        return str(v) + ' kg'
    elif unitat == 'l':
        if val < 1:
            return str(int(val * 1000)) + ' ml'
        v = int(val) if val == int(val) else val
        return str(v) + ' l'
    return pes_text


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


def scrape_recursiu(driver, url, nivell=0, totals=None):
    if totals is None:
        totals = []
    prefix = '  ' * (nivell + 2)
    try:
        driver.get(url)
        time.sleep(3)
        subcats = get_subcategories(driver, url)
        nom_cat = url.split('/')[-2]

        if subcats:
            print(f"{prefix}📂 {nom_cat}: {len(subcats)} subcategories")
            for nom_sub, url_sub in subcats:
                scrape_recursiu(driver, url_sub, nivell + 1, totals)
        else:
            productes = extreure_productes_pagina(driver, url)
            print(f"{prefix}└ {nom_cat}: {len(productes)} productes")
            if productes:
                print(f"{prefix}   Exemple: {productes[0]}")
            totals.append((nom_cat, len(productes)))
    except Exception as e:
        nom_cat = url.split('/')[-2]
        print(f"{prefix}❌ Error {nom_cat}: {e}")
    return totals


def main():
    driver = Driver(uc=True, headed=True)
    try:
        print(f"🌐 Obrint {BASE_URL} amb SeleniumBase UC Mode + Xvfb ...")
        driver.uc_open_with_reconnect(BASE_URL, reconnect_time=6)
        time.sleep(3)

        driver.add_cookie({
            "name": "language",
            "value": "ca",
            "domain": "www.compraonline.bonpreuesclat.cat"
        })
        driver.refresh()
        time.sleep(6)

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
            totals = scrape_recursiu(driver, url_cat, nivell=0)
            subtotal = sum(n for _, n in totals)
            gran_total += subtotal
            print(f"  ✅ Total {nom_cat}: {subtotal} productes\n")

        print(f"\n🏁 GRAN TOTAL ({', '.join(CATEGORIES_A_PROVAR)}): {gran_total} productes")

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
