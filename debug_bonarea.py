from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

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
driver.get('https://www.carrefour.es/supermercado/frescos/cat20002/c?offset=0')
time.sleep(10)
for i in range(3):
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(2)

noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')
preus = driver.find_elements(By.CSS_SELECTOR, 'span.product-card__price')
print(f"Productes: {len(noms)}")
for i in range(min(5, len(noms))):
    nom = noms[i].get_attribute('innerText').strip()
    preu = preus[i].get_attribute('innerText').strip() if i < len(preus) else ''
    print(f"\n  Nom: {nom}")
    print(f"  Preu: {preu}")
    # Busquem camps de quantitat específics
    pare = driver.execute_script("return arguments[0].closest('.product-card')", noms[i])
    if pare:
        for selector in ['span.product-card__unit', 'div.product-card__quantity',
                        'span.product-card__weight', 'p.product-card__description',
                        'span[class*="unit"]', 'span[class*="weight"]', 'span[class*="quantity"]']:
            try:
                el = pare.find_element(By.CSS_SELECTOR, selector)
                print(f"  [{selector}]: {el.get_attribute('innerText').strip()}")
            except:
                pass

driver.quit()
