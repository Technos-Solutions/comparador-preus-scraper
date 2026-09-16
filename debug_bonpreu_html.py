# debug_bonpreu_html.py — Script de només diagnòstic, NO toca cap dada
# ni el scraper de producció. El scraper de producció força un cookie
# 'language: es-ES', per això les categories surten en castellà i el
# filtre en català (categories_valides) no hi encaixa. Aquest script
# prova diverses maneres d'entrar en català (URL /ca/home suggerida per
# l'usuari, i cookie language=ca) per veure quina dona categories en
# català abans de tocar el scraper de producció.

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'

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
driver = webdriver.Chrome(service=service, options=chrome_options)


def informa(etiqueta):
    titol = driver.title
    url_final = driver.current_url
    html = driver.page_source
    print(f"\n=== {etiqueta} ===")
    print(f"📄 Títol de la pàgina: {titol!r}")
    print(f"🔗 URL final (després de possibles redireccions): {url_final}")
    print(f"📏 Mida de l'HTML: {len(html)} caràcters")
    links_categories = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
    print(f"🔎 Elements 'a[href*=\"/categories/\"]' trobats: {len(links_categories)}")
    for link in links_categories[:15]:
        print(f"    - {link.get_attribute('innerText').strip()!r} -> {link.get_attribute('href')}")
    paraules_sospitoses = ['captcha', 'robot', 'unusual traffic', 'access denied', 'blocked',
                            'aceptar cookies', 'consentimiento', 'consent', 'akamai', 'cloudflare',
                            'datadome', 'perimeterx', 'incapsula']
    trobades = [p for p in paraules_sospitoses if p in html.lower()]
    print(f"⚠️  Paraules sospitoses trobades a l'HTML: {trobades if trobades else 'cap'}")
    return html


# PROVA 1: entrar directament per la URL en català que suggereix l'usuari
print("🌐 PROVA 1: navegant a https://www.bonpreuesclat.cat/ca/home ...")
driver.get('https://www.bonpreuesclat.cat/ca/home')
time.sleep(6)
html1 = informa("PROVA 1: bonpreuesclat.cat/ca/home")
driver.save_screenshot('bonpreu_debug_prova1.png')
with open('bonpreu_debug_prova1.html', 'w', encoding='utf-8') as f:
    f.write(html1)

# PROVA 2: base_url actual del scraper pero amb cookie language=ca en lloc de es-ES
print("\n🌐 PROVA 2: compraonline.bonpreuesclat.cat amb cookie language=ca ...")
driver.get(BASE_URL)
driver.add_cookie({
    "name": "language",
    "value": "ca",
    "domain": "www.compraonline.bonpreuesclat.cat"
})
driver.refresh()
time.sleep(8)
html2 = informa("PROVA 2: compraonline + cookie language=ca")
driver.save_screenshot('bonpreu_debug_prova2.png')
with open('bonpreu_debug_prova2.html', 'w', encoding='utf-8') as f:
    f.write(html2)

print("\n✅ Fet.")
driver.quit()
