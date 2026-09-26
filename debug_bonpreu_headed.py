# debug_bonpreu_headed.py — Script de només diagnòstic, NO toca cap dada
# ni el scraper de producció. El diagnostic anterior (debug_bonpreu_
# subcategories.py) va confirmar que les pagines de categoria de Bon
# Preu/Esclat (per exemple 'Frescos') no mostren els productes, sino una
# pantalla "Human Verification" (deteccio de Selenium en mode headless).
# Aquest script prova el mateix truc que ja va funcionar parcialment amb
# Carrefour: SeleniumBase amb UC Mode + Chrome real (headed) via Xvfb, en
# lloc de --headless, per veure si aixo sol ja evita la verificacio.

import time
from seleniumbase import Driver

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'
URL_CATEGORIA = 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11'

driver = Driver(uc=True, headed=True)

try:
    print(f"🌐 Obrint {BASE_URL} amb SeleniumBase UC Mode + Xvfb ...")
    driver.uc_open_with_reconnect(BASE_URL, reconnect_time=6)
    time.sleep(3)

    print("🍪 Afegint cookie language=ca ...")
    driver.add_cookie({
        "name": "language",
        "value": "ca",
        "domain": "www.compraonline.bonpreuesclat.cat"
    })
    driver.refresh()
    time.sleep(5)

    print(f"🌐 Navegant a la categoria: {URL_CATEGORIA}")
    driver.uc_open_with_reconnect(URL_CATEGORIA, reconnect_time=6)
    time.sleep(4)

    print("📜 Fent scroll per activar la carrega de productes ...")
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)
    time.sleep(3)

    titol = driver.get_title()
    url_final = driver.get_current_url()
    html = driver.get_page_source()

    print(f"📄 Titol de la pagina: {titol!r}")
    print(f"🔗 URL final: {url_final}")
    print(f"📏 Mida de l'HTML: {len(html)} caracters")

    noms = driver.find_elements('h3[data-test="fop-title"]')
    preus = driver.find_elements('span[data-test="fop-price"]')
    print(f"🔎 h3[data-test='fop-title'] trobats: {len(noms)}")
    print(f"🔎 span[data-test='fop-price'] trobats: {len(preus)}")

    if noms:
        print(f"   Exemple de producte: {noms[0].text!r}")

    paraules_sospitoses = ['captcha', 'robot', 'human verification', 'verificaci', 'blocked', 'access denied']
    trobades = [p for p in paraules_sospitoses if p in html.lower()]
    print(f"⚠️  Paraules sospitoses trobades: {trobades if trobades else 'cap'}")

    driver.save_screenshot('bonpreu_headed_debug.png')
    with open('bonpreu_headed_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Captura desada a bonpreu_headed_debug.png i HTML a bonpreu_headed_debug.html")

finally:
    driver.quit()
