# debug_carrefour_categoria.py — Script de nomes diagnostic, NO toca cap
# dada ni el scraper de produccio. Validacio completa d'una categoria de
# Carrefour abans de corregir CarrefourScraper:
#   - SeleniumBase UC Mode + Xvfb (el Selenium headless de produccio queda
#     aturat a la pantalla "Just a moment..." de Cloudflare)
#   - Selectors nous: <div data-origin="list" app_price="..." ...>, amb el
#     nom a l'atribut alt de la imatge (el selector antic
#     article[data-test="search-grid-result"] ja no existeix)
# Es valida el CONTINGUT (noms i preus reals), no nomes el recompte:
#   - quants productes carrega cada pagina despres de fer scroll
#   - si la paginacio ?offset=N dona productes nous o repetits
#   - si hi ha targetes duplicades dins la mateixa pagina
#   - quants productes diu la pagina que te la categoria

import re
import time
from seleniumbase import Driver

BASE = 'https://www.carrefour.es/supermercado/frescos/cat20002/c'
PAS_OFFSET = 24
MAX_PAGINES = 8


def carregar_tota_la_pagina(driver):
    anterior = -1
    for _ in range(15):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1.5)
        actual = len(driver.find_elements('div[data-origin="list"]'))
        if actual == anterior:
            break
        anterior = actual
    return anterior


def llegir_productes(driver):
    productes = []
    for card in driver.find_elements('div[data-origin="list"]'):
        try:
            preu = card.get_attribute('app_price') or ''
            preu_unitat = card.get_attribute('app_price_per_unit') or ''
            marca = card.get_attribute('brand') or ''
            nom = ''
            link = ''
            imgs = card.find_elements('css selector', 'img.product-card__image')
            if imgs:
                nom = (imgs[0].get_attribute('alt') or '').strip()
            links = card.find_elements('css selector', 'a.product-card__media-link')
            if links:
                link = links[0].get_attribute('href') or ''
            productes.append({'nom': nom, 'preu': preu, 'preu_unitat': preu_unitat,
                              'marca': marca, 'link': link})
        except Exception as e:
            productes.append({'error': str(e)})
    return productes


def main():
    driver = Driver(uc=True, headed=True)
    vistos_links = set()
    total_nous = 0
    try:
        for pagina in range(MAX_PAGINES):
            offset = pagina * PAS_OFFSET
            url = f'{BASE}?offset={offset}'
            print(f"\n=== offset={offset} ===")
            if pagina == 0:
                driver.uc_open_with_reconnect(url, reconnect_time=6)
                time.sleep(3)
                try:
                    driver.click('#onetrust-accept-btn-handler', timeout=8)
                    time.sleep(2)
                except Exception:
                    pass
            else:
                driver.get(url)
                time.sleep(5)

            titol = driver.get_title()
            print(f"Titol: {titol!r}")
            if 'just a moment' in titol.lower():
                print("⛔ Bloquejat per Cloudflare en aquesta pagina, parant")
                break

            if pagina == 0:
                html = driver.get_page_source()
                m = re.findall(r'(\d[\d\.]*)\s+(?:productos|resultados)', html)
                print(f"Recompte de productes que mostra la pagina: {m[:5]}")

            n = carregar_tota_la_pagina(driver)
            productes = llegir_productes(driver)
            errors = [p for p in productes if 'error' in p]
            valids = [p for p in productes if p.get('nom') and p.get('preu')]
            sense_nom = [p for p in productes if 'error' not in p and not p.get('nom')]
            links_pagina = [p['link'] for p in valids]
            duplicats_pagina = len(links_pagina) - len(set(links_pagina))
            nous = [p for p in valids if p['link'] not in vistos_links]
            vistos_links.update(links_pagina)
            total_nous += len(nous)

            print(f"Targetes despres de scroll: {n}")
            print(f"Valids (nom+preu): {len(valids)} | sense nom: {len(sense_nom)} | errors: {len(errors)}")
            print(f"Duplicats dins la pagina: {duplicats_pagina}")
            print(f"Nous respecte pagines anteriors: {len(nous)}")
            for p in valids[:3]:
                print(f"   - {p['nom']!r} | {p['preu']} | {p['preu_unitat']} | marca={p['marca']!r}")
            if sense_nom:
                print(f"   Exemple sense nom: {sense_nom[0]}")

            if not nous:
                print("Cap producte nou: fi de la paginacio (o offset no funciona)")
                break

        print(f"\n🏁 Total productes unics a la categoria (fins a {MAX_PAGINES} pagines): {total_nous}")
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
