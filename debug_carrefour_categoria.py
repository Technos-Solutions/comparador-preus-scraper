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

CATEGORIES = [
    ('https://www.carrefour.es/supermercado/frescos/cat20002/c', 12),
    ('https://www.carrefour.es/supermercado/la-despensa/cat20001/c', 3),
]
PAS_OFFSET = 24


def superar_cloudflare(driver, url, max_intents=3):
    """Cloudflare mostra el repte 'Just a moment...' de forma intermitent
    (el mateix script passa un cop i l'altre no). Espera que es resolgui
    sol, clica la casella si n'hi ha, i si cal reconnecta. Retorna True si
    s'ha arribat a la pagina real, i imprimeix quin pas ho ha resolt."""
    for intent in range(1, max_intents + 1):
        for segon in range(0, 20, 2):
            if 'just a moment' not in driver.get_title().lower():
                print(f"   ✅ Pagina real (intent {intent}, {segon}s d'espera)")
                return True
            time.sleep(2)
        print(f"   ⏳ Encara 'Just a moment...' (intent {intent}), clicant casella de Cloudflare...")
        try:
            driver.uc_gui_click_cf()
            time.sleep(4)
        except Exception as e:
            print(f"   (uc_gui_click_cf: {e})")
        if 'just a moment' not in driver.get_title().lower():
            print(f"   ✅ Pagina real despres de clicar la casella (intent {intent})")
            return True
        print(f"   🔄 Reconnectant (intent {intent})...")
        driver.uc_open_with_reconnect(url, reconnect_time=8)
        time.sleep(3)
    return False


def carregar_tota_la_pagina(driver):
    # Scroll pas a pas (no saltant directament al final): la graella es
    # renderitza a mesura que les targetes entren a la pantalla, i saltar
    # al final deixava pagines amb nomes 13 de 24 targetes carregades.
    estable = 0
    anterior = -1
    for _ in range(40):
        driver.execute_script('window.scrollBy(0, 600);')
        time.sleep(0.8)
        actual = len(driver.find_elements('div[data-origin="list"]'))
        al_final = driver.execute_script(
            'return window.innerHeight + window.scrollY >= document.body.scrollHeight - 50;')
        if actual == anterior and al_final:
            estable += 1
            if estable >= 2:
                break
        else:
            estable = 0
        anterior = actual
    return anterior


def classificar_contenidors(driver):
    # Distingeix targetes de la graella principal de les de carrusels
    # (recomanats, promocions...) que poden fer servir el mateix format.
    return driver.execute_script("""
        const cards = document.querySelectorAll('div[data-origin="list"]');
        const compte = {};
        cards.forEach(c => {
            const ul = c.closest('ul');
            const sec = c.closest('section, [class*="carousel"], [class*="slider"]');
            const clau = (ul ? ul.className : 'sense-ul') + ' || ' +
                         (sec ? (sec.className || sec.tagName) : 'sense-seccio');
            compte[clau] = (compte[clau] || 0) + 1;
        });
        return compte;
    """)


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


def provar_categoria(driver, base, max_pagines, primera):
    print(f"\n\n######## {base} ########")
    vistos = {}
    total_nous = 0
    for pagina in range(max_pagines):
        offset = pagina * PAS_OFFSET
        url = f'{base}?offset={offset}'
        print(f"\n=== offset={offset} ===")
        if primera and pagina == 0:
            driver.uc_open_with_reconnect(url, reconnect_time=6)
        else:
            driver.get(url)
        time.sleep(3)

        if not superar_cloudflare(driver, url):
            print("⛔ No s'ha pogut superar Cloudflare despres de 3 intents, parant")
            return

        if primera and pagina == 0:
            try:
                driver.click('#onetrust-accept-btn-handler', timeout=8)
                time.sleep(2)
            except Exception:
                pass

        print(f"Titol: {driver.get_title()!r}")
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
        nous = [p for p in valids if p['link'] not in vistos]
        repetits = [p for p in valids if p['link'] in vistos]
        for p in valids:
            vistos.setdefault(p['link'], offset)
        total_nous += len(set(p['link'] for p in nous))

        print(f"Targetes despres de scroll: {n}")
        print(f"Contenidors: {classificar_contenidors(driver)}")
        print(f"Valids (nom+preu): {len(valids)} | sense nom: {len(sense_nom)} | errors: {len(errors)}")
        print(f"Duplicats dins la pagina: {duplicats_pagina}")
        print(f"Nous: {len(nous)} | Repetits de pagines anteriors: {len(repetits)}")
        for p in repetits[:6]:
            print(f"   ↩ repetit (vist a offset={vistos[p['link']]}): {p['nom']!r}")
        for p in valids[:2]:
            print(f"   - {p['nom']!r} | {p['preu']} | {p['preu_unitat']} | marca={p['marca']!r}")
        if sense_nom:
            print(f"   Exemple sense nom: {sense_nom[0]}")

        if not nous:
            print("Cap producte nou: fi de la paginacio (o offset no funciona)")
            break

    print(f"\n🏁 Total productes unics ({max_pagines} pagines max): {total_nous}")


def main():
    driver = Driver(uc=True, headed=True)
    try:
        for i, (base, max_pagines) in enumerate(CATEGORIES):
            provar_categoria(driver, base, max_pagines, primera=(i == 0))
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
