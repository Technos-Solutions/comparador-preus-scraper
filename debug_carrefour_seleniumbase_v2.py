# debug_carrefour_seleniumbase_v2.py — Script de nomes diagnostic, NO
# toca cap dada ni el scraper de produccio. Fa mesos, SeleniumBase (UC
# Mode + Xvfb, sense cap servei de pagament) va aconseguir carregar la
# pagina real de Carrefour pero la consola del navegador mostrava
# errors de xarxa explicits (403) per a la crida interna que omple la
# graella de productes (plp-food-papi). En paral·lel, hem descobert que
# el selector que fem servir per comptar productes
# (data-test="search-grid-result") esta obsolet - Carrefour ara fa
# servir <div data-origin="list" app_price="..." brand="..." ...>.
# Abans de concloure que cal un servei de pagament (ZenRows), aquest
# script torna a provar NOMES amb SeleniumBase (gratuit) pero buscant
# el selector nou, per descartar que el "bloqueig" real nomes fos un
# fals negatiu per selector desactualitzat.

import time
from seleniumbase import Driver

URL = 'https://www.carrefour.es/supermercado/frescos/cat20002/c'

driver = Driver(uc=True, headed=True)

try:
    print(f"🌐 Obrint {URL} amb SeleniumBase UC Mode + Xvfb ...")
    driver.uc_open_with_reconnect(URL, reconnect_time=6)
    time.sleep(4)

    try:
        driver.uc_gui_click_cf()
        time.sleep(3)
    except Exception as e:
        print(f"   (no hi havia checkbox de Cloudflare o no s'ha pogut clicar: {e})")

    try:
        driver.click("#onetrust-accept-btn-handler", timeout=8)
        print("   ✅ Banner de cookies acceptat")
        time.sleep(3)
    except Exception as e:
        print(f"   (no s'ha trobat/clicat el banner de cookies: {e})")

    for i in range(3):
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(2)

    titol = driver.get_title()
    html = driver.get_page_source()
    print(f"📄 Titol: {titol!r}")
    print(f"📏 Mida HTML: {len(html)} caracters")

    # Selector VELL (el que fem servir habitualment als debug scripts)
    vells = driver.find_elements('article[data-test="search-grid-result"]')
    print(f"🔎 Selector VELL 'article[data-test=\"search-grid-result\"]': {len(vells)} trobats")

    # Selector NOU (descobert amb ZenRows aquesta mateixa sessio)
    nous = driver.find_elements('div[data-origin="list"]')
    print(f"🔎 Selector NOU 'div[data-origin=\"list\"]': {len(nous)} trobats")

    if nous:
        primer = nous[0]
        print(f"   Exemple atribut app_price: {primer.get_attribute('app_price')!r}")
        print(f"   Exemple atribut brand: {primer.get_attribute('brand')!r}")

    # Comprovacio addicional: errors de consola (com fa mesos)
    try:
        logs = driver.get_log('browser')
        errors_403 = [l for l in logs if '403' in str(l.get('message', ''))]
        print(f"⚠️  Errors de consola amb '403': {len(errors_403)}")
        for e in errors_403[:5]:
            print(f"   {e.get('message', '')[:200]}")
    except Exception as e:
        print(f"   (no s'han pogut llegir els logs del navegador: {e})")

    paraules_sospitoses = ['captcha', 'robot', 'just a moment', 'checking your browser']
    trobades = [p for p in paraules_sospitoses if p in html.lower()]
    print(f"⚠️  Paraules sospitoses a l'HTML: {trobades if trobades else 'cap'}")

    driver.save_screenshot('carrefour_seleniumbase_v2.png')
    with open('carrefour_seleniumbase_v2.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Captura i HTML desats")

finally:
    driver.quit()
