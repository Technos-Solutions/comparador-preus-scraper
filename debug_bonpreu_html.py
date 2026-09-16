# debug_bonpreu_html.py — Script de només diagnòstic, NO toca cap dada
# ni el scraper de producció. Reprodueix exactament els primers passos de
# BonPreuEsclatScraper.descobrir_categories() (mateixes opcions de Chrome,
# mateixa cookie de idioma, mateix temps d'espera) i desa una captura de
# pantalla + l'HTML complet tal com el veu el runner de GitHub Actions,
# per esbrinar per què el scraper de producció porta setmanes donant 0
# productes de Bon Preu/Esclat (confirmat almenys des del 24 d'agost).

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

print(f"🌐 Carregant {BASE_URL} ...")
driver.get(BASE_URL)
driver.add_cookie({
    "name": "language",
    "value": "es-ES",
    "domain": "www.compraonline.bonpreuesclat.cat"
})
driver.refresh()
time.sleep(8)

titol = driver.title
url_final = driver.current_url
html = driver.page_source

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

driver.save_screenshot('bonpreu_debug.png')
with open('bonpreu_debug.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Captura desada a bonpreu_debug.png i HTML a bonpreu_debug.html")

driver.quit()
