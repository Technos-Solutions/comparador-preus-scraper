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

    # La pagina carrega el CMP de OneTrust (cdn.cookielaw.org / OptanonWrapper).
    # Si el banner de cookies queda sense resposta, es possible que el Vue de
    # la graella de productes no arribi a muntar-se. OneTrust fa servir sempre
    # el mateix id estandard pel boto "Acceptar totes".
    try:
        print("🍪 Intentant acceptar el banner de cookies (OneTrust)...")
        driver.click("#onetrust-accept-btn-handler", timeout=8)
        print("   ✅ Banner de cookies acceptat")
        time.sleep(3)
    except Exception as e:
        print(f"   (no s'ha trobat/clicat el banner de OneTrust: {e})")

    print("📜 Fent scroll per activar la càrrega de productes (com fa el scraper real)...")
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(2)
    time.sleep(5)

    titol = driver.get_title()
    url_final = driver.get_current_url()
    html = driver.get_page_source()

    print(f"📄 Títol de la pàgina: {titol!r}")
    print(f"🔗 URL final: {url_final}")
    print(f"📏 Mida de l'HTML: {len(html)} caràcters")

    articles = driver.find_elements('article[data-test="search-grid-result"]')
    print(f"🔎 Elements 'article[data-test=\"search-grid-result\"]' trobats: {len(articles)}")

    # Diagnostic extra: quants <article> hi ha en total (amb qualsevol atribut)?
    tots_articles = driver.find_elements('article')
    print(f"🔎 Elements 'article' (qualsevol) trobats: {len(tots_articles)}")

    # Quins data-test existeixen realment a la pagina?
    amb_data_test = driver.find_elements('[data-test]')
    valors_data_test = sorted(set(
        el.get_attribute('data-test') for el in amb_data_test if el.get_attribute('data-test')
    ))
    print(f"🔎 Valors 'data-test' trobats a la pagina ({len(valors_data_test)}): {valors_data_test[:40]}")

    # Hi ha un banner de cookies/consentiment visible?
    for terme in ['aceptar', 'cookie', 'consent', 'onetrust', 'cookiebot', 'didomi']:
        idx = html.lower().find(terme)
        if idx != -1:
            print(f"   🍪 Trobat '{terme}' a la posicio {idx}: ...{html[max(0,idx-80):idx+80]}...")

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
