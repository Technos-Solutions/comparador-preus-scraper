# debug_carrefour_html.py — Script de només diagnòstic, NO toca cap dada
# ni el scraper de producció. Carrega una pàgina de Carrefour amb el mateix
# Selenium/Chrome que fa servir servicio scraper_main.py des de GitHub
# Actions i desa una captura de pantalla + l'HTML complet tal com el veu
# el runner, per esbrinar per què el scraper de producció obté 0 productes
# tot i tenir els selectors correctes (verificats amb HTML real des d'un
# navegador normal). Si Carrefour bloqueja/repta els navegadors headless
# de GitHub Actions, aquí ho veurem (pàgina buida, mur de consentiment,
# captcha, etc.).

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

URL = 'https://www.carrefour.es/supermercado/la-despensa/cat20001/c?offset=0'

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--allow-running-insecure-content')
chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
chrome_options.binary_location = '/usr/bin/chromium-browser'
service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

print(f"🌐 Carregant {URL} ...")
driver.get(URL)
time.sleep(10)
for _ in range(3):
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(2)

titol = driver.title
url_final = driver.current_url
html = driver.page_source

print(f"📄 Títol de la pàgina: {titol!r}")
print(f"🔗 URL final (després de possibles redireccions): {url_final}")
print(f"📏 Mida de l'HTML: {len(html)} caràcters")

articles = driver.find_elements(By.CSS_SELECTOR, 'article[data-test="search-grid-result"]')
print(f"🔎 Elements 'article[data-test=\"search-grid-result\"]' trobats: {len(articles)}")

paraules_sospitoses = ['captcha', 'robot', 'unusual traffic', 'access denied', 'blocked', 'cookies', 'consent', 'akamai', 'cloudflare', 'datadome', 'perimeterx']
trobades = [p for p in paraules_sospitoses if p in html.lower()]
print(f"⚠️  Paraules sospitoses trobades a l'HTML: {trobades if trobades else 'cap'}")

driver.save_screenshot('carrefour_debug.png')
with open('carrefour_debug.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Captura desada a carrefour_debug.png i HTML a carrefour_debug.html")

driver.quit()
