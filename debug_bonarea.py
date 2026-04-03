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
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat/categories/alimentaci%C3%B3/c49d1ef2-bf51-44a7-b631-4a35474a21ac')
time.sleep(12)
for i in range(5):
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(2)

noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
preus = driver.find_elements(By.CSS_SELECTOR, 'span[data-test="fop-price"]')
print(f"Productes: {len(noms)}")

for i in range(min(5, len(noms))):
    nom = noms[i].get_attribute('innerText').strip()
    preu = preus[i].get_attribute('innerText').strip() if i < len(preus) else ''
    # Busquem el selector de quantitat
    contenidor = noms[i].find_element(By.XPATH, '../../../..')
    for sel in ['[data-test="fop-weight"]', '[data-test="fop-unit-price"]',
                'p[class*="weight"]', 'span[class*="weight"]',
                'p[class*="unit"]', 'span[class*="unit"]']:
        try:
            el = contenidor.find_element(By.CSS_SELECTOR, sel)
            print(f"  [{sel}]: {el.get_attribute('innerText').strip()}")
        except:
            pass
    print(f"  Nom: {nom} | Preu: {preu}")
    print()

driver.quit()
