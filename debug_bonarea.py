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
print(f"Productes trobats: {len(noms)}")
if noms:
    # Imprimim el HTML del contenidor del primer producte
    pare = driver.execute_script("return arguments[0].closest('.product-card')", noms[0])
    if pare:
        print("\nHTML primer producte:")
        print(pare.get_attribute('innerHTML')[:2000])
    else:
        print("\nText primer producte:", noms[0].get_attribute('innerText'))

driver.quit()
