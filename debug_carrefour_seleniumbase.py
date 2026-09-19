# debug_carrefour_seleniumbase.py — Script de només diagnòstic, NO toca cap
# dada ni el scraper de producció. Prova SeleniumBase amb UC Mode (Chrome
# "no detectable") + Xvfb (pantalla virtual, perquè Cloudflare sembla
# detectar el mode headless en si, no tant la IP de GitHub Actions -
# confirmat: Mercadona/Dia/Bon Àrea no tenen aquest problema des de la
# mateixa infraestructura). Desa captura + HTML per confirmar si es
# veuen productes reals de Carrefour abans de tocar scraper_main.py.

import time
from seleniumbase import Driver

URL = 'https://www.carrefour.es/supermercado/la-despensa/cat20001/c?offset=0'

driver = Driver(uc=True, headed=True)

try:
    print(f"🌐 Obrint {URL} amb SeleniumBase UC Mode + Xvfb ...")
    driver.uc_open_with_reconnect(URL, reconnect_time=6)
    time.sleep(4)

    try:
        print("🖱️  Intentant clicar el checkbox de Cloudflare (si n'hi ha)...")
        driver.uc_gui_click_cf()
        time.sleep(3)
    except Exception as e:
        print(f"   (no hi havia checkbox o no s'ha pogut clicar: {e})")

    titol = driver.get_title()
    url_final = driver.get_current_url()
    html = driver.get_page_source()

    print(f"📄 Títol de la pàgina: {titol!r}")
    print(f"🔗 URL final: {url_final}")
    print(f"📏 Mida de l'HTML: {len(html)} caràcters")

    articles = driver.find_elements('article[data-test="search-grid-result"]')
    print(f"🔎 Elements 'article[data-test=\"search-grid-result\"]' trobats: {len(articles)}")

    if articles:
        primer = articles[0]
        try:
            nom = primer.find_element('a[data-test="result-title"]').text.strip()
            preu = primer.find_element('div[data-test="result-current-price"]').text.strip()
            print(f"   ✅ Exemple de producte: {nom!r} — {preu!r}")
        except Exception as e:
            print(f"   ⚠️ No s'ha pogut llegir nom/preu del primer article: {e}")

    paraules_sospitoses = ['captcha', 'robot', 'unusual traffic', 'access denied', 'blocked',
                            'consent', 'cloudflare', 'checking your browser', 'just a moment']
    trobades = [p for p in paraules_sospitoses if p in html.lower()]
    print(f"⚠️  Paraules sospitoses trobades a l'HTML: {trobades if trobades else 'cap'}")

    driver.save_screenshot('carrefour_uc_debug.png')
    with open('carrefour_uc_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Captura desada a carrefour_uc_debug.png i HTML a carrefour_uc_debug.html")

finally:
    driver.quit()
