# debug_bonpreu_subcategories.py — Script de només diagnòstic, NO toca
# cap dada ni el scraper de producció. El fix anterior (cookie
# language=ca) ja fa que descobrir_categories() trobi les 11 categories
# principals en català correctament. Pero un cop es baixa a les
# subcategories i s'intenta extreure productes amb els selectors
# h3[data-test="fop-title"] / span[data-test="fop-price"], el compte
# surt a 0. Aquest script reprodueix exactament la mateixa lògica de
# recursivitat i extracció que scraper_main.py (BonPreuEsclatScraper)
# pero amb molta més informació de diagnòstic a cada pas, per veure on
# es trenca exactament: descobriment de subcategories, càrrega de la
# pàgina final, o els selectors de nom/preu.

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'


def crear_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)


def get_subcategories(driver, url):
    path_pare = url.split('/categories/')[-1].split('?')[0]
    segments_pare = [s for s in path_pare.split('/') if s]
    slug_pare = segments_pare[0]
    n_segments_pare = len(segments_pare)

    links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
    subcats = []
    uuids_vistos = set()
    for link in links:
        href = link.get_attribute('href') or ''
        text = link.get_attribute('innerText').strip()
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


def diagnosticar_pagina_final(driver, url, etiqueta):
    print(f"\n=== {etiqueta}: {url} ===")
    driver.get(url)
    time.sleep(4)
    anterior = 0
    for i in range(5):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)
        actual = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
        if actual == anterior and i > 1:
            break
        anterior = actual

    titol = driver.title
    html = driver.page_source
    print(f"Titol de la pagina: {titol!r}")
    print(f"Mida de l'HTML: {len(html)} caracters")

    noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
    preus = driver.find_elements(By.CSS_SELECTOR, 'span[data-test="fop-price"]')
    print(f"h3[data-test='fop-title'] trobats: {len(noms)}")
    print(f"span[data-test='fop-price'] trobats: {len(preus)}")

    # Selectors alternatius per si data-test ha canviat
    alternatives = [
        ('[data-test="fop-title"] (qualsevol tag)', '[data-test="fop-title"]'),
        ('[data-test="fop-price"] (qualsevol tag)', '[data-test="fop-price"]'),
        ('[data-test*="fop"]', '[data-test*="fop"]'),
        ('[class*="product"]', '[class*="product"]'),
        ('article', 'article'),
    ]
    for nom_sel, sel in alternatives:
        try:
            n = len(driver.find_elements(By.CSS_SELECTOR, sel))
            print(f"  Alternatiu {nom_sel}: {n} elements")
        except Exception as e:
            print(f"  Alternatiu {nom_sel}: error {e}")

    paraules_sospitoses = ['captcha', 'robot', 'unusual traffic', 'access denied', 'blocked',
                            'no hem trobat', 'no s\'ha trobat', 'sense resultats', 'no results',
                            'inici de sessi', 'iniciar sessi', 'log in', 'consentiment']
    trobades = [p for p in paraules_sospitoses if p in html.lower()]
    print(f"Paraules sospitoses trobades: {trobades if trobades else 'cap'}")

    nom_fitxer = etiqueta.lower().replace(' ', '_').replace('/', '_')
    driver.save_screenshot(f'bonpreu_sub_{nom_fitxer}.png')
    with open(f'bonpreu_sub_{nom_fitxer}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Captura desada: bonpreu_sub_{nom_fitxer}.png / .html")


def main():
    driver = crear_driver()
    try:
        driver.get(BASE_URL)
        driver.add_cookie({
            "name": "language",
            "value": "ca",
            "domain": "www.compraonline.bonpreuesclat.cat"
        })
        driver.refresh()
        time.sleep(8)

        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
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
            if any(cat in text for cat in ['frescos', 'alimentaci', 'begudes']):
                uuids_vistos.add(uuid)
                url_neta = f"{BASE_URL}/categories/{href.split('/categories/')[1].split('?')[0]}"
                categories.append((text.title(), url_neta))

        print(f"Categories principals trobades (mostra): {categories}")

        if not categories:
            print("No s'ha trobat cap categoria principal, aturant.")
            return

        nom_cat, url_cat = categories[0]
        print(f"\nUsant categoria principal: {nom_cat} -> {url_cat}")

        driver.get(url_cat)
        time.sleep(5)
        for i in range(2):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)

        subcats_nivell1 = get_subcategories(driver, url_cat)
        print(f"Subcategories nivell 1 de {nom_cat}: {len(subcats_nivell1)}")
        for nom_sub, url_sub in subcats_nivell1:
            print(f"  - {nom_sub} -> {url_sub}")

        if not subcats_nivell1:
            diagnosticar_pagina_final(driver, url_cat, f"categoria_arrel_{nom_cat}")
            return

        # Baixem un nivell mes per veure si hi ha subcategories de segon nivell
        nom_sub1, url_sub1 = subcats_nivell1[0]
        driver.get(url_sub1)
        time.sleep(5)
        for i in range(2):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)
        subcats_nivell2 = get_subcategories(driver, url_sub1)
        print(f"\nSubcategories nivell 2 de {nom_sub1}: {len(subcats_nivell2)}")
        for nom_sub2, url_sub2 in subcats_nivell2:
            print(f"  - {nom_sub2} -> {url_sub2}")

        if subcats_nivell2:
            nom_final, url_final = subcats_nivell2[0]
        else:
            nom_final, url_final = nom_sub1, url_sub1

        diagnosticar_pagina_final(driver, url_final, f"final_{nom_final}")

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
