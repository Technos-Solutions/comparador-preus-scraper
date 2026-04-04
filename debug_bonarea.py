from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re

def crear_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

# ============================================================
# TEST 1 - DIA: categoria + subcategories
# ============================================================
print('TEST 1 - DIA')
driver = crear_driver()
driver.get('https://www.dia.es/verduras/c/L104')
time.sleep(8)
links = driver.find_elements(By.TAG_NAME, 'a')
subcats = set()
for link in links:
    href = link.get_attribute('href') or ''
    if re.search(r'dia\.es/[^/]+/[^/]+/c/L\d+$', href):
        subcats.add(href)
driver.quit()
print(f'  Verduras: {len(subcats)} subcategories trobades')

# Rasquem la primera subcategoria
url_sub = list(subcats)[0]
driver = crear_driver()
driver.get(url_sub)
time.sleep(8)
anterior = 0
for i in range(6):
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
    time.sleep(2)
    actual = len(driver.find_elements(By.CSS_SELECTOR, '.search-product-card'))
    if actual == anterior and i > 1:
        break
    anterior = actual
cards = driver.find_elements(By.CSS_SELECTOR, '.search-product-card')
print(f'  Primera subcategoria: {len(cards)} productes')
if cards:
    try:
        nom = cards[0].find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-name"]').get_attribute('innerText').strip()
        print(f'  Exemple: {nom}')
    except:
        pass
driver.quit()

# ============================================================
# TEST 2 - CARREFOUR: paginació fins a offset 200
# ============================================================
print('\nTEST 2 - CARREFOUR')
total = 0
for offset in [0, 24, 48, 72, 96, 120, 144, 168, 192]:
    driver = crear_driver()
    url = f'https://www.carrefour.es/supermercado/frescos/cat20002/c?offset={offset}'
    driver.get(url)
    time.sleep(10)
    for i in range(3):
        driver.execute_script('window.scrollBy(0, 400)')
        time.sleep(2)
    noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')
    noms_text = [n.get_attribute('innerText').strip() for n in noms]
    driver.quit()
    if not noms_text:
        print(f'  offset={offset} -> 0 productes, FI')
        break
    total += len(noms_text)
    print(f'  offset={offset} -> {len(noms_text)} productes')
print(f'  Total Carrefour frescos: {total} productes')

# ============================================================
# TEST 3 - BON PREU/ESCLAT: categories trobades
# ============================================================
print('\nTEST 3 - BON PREU/ESCLAT')
categories_valides = [
    'frescos', 'alimentaci', 'begudes', 'congelats',
    'ctics', 'cura', 'neteja', 'per la llar',
    'mascotes', 'nadons', 'parafarm',
]
driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat')
time.sleep(8)
links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
categories = []
uuids_vistos = set()
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip().lower()
    uuid = href.split('/')[-1].split('?')[0]
    if uuid not in uuids_vistos and text and len(uuid) > 10:
        if any(cat in text for cat in categories_valides):
            uuids_vistos.add(uuid)
            categories.append(text.title())
driver.quit()
print(f'  Categories trobades: {len(categories)}')
for c in categories:
    print(f'    ✅ {c}')
