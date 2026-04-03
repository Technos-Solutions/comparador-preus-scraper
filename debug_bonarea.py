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
driver.get('https://www.bonarea-online.com/categories/llegums-secs-i-arrossos/13_300_100_010')
time.sleep(8)
for i in range(3):
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(1)

productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
print(f"Productes trobats: {len(productes)}")
for prod in productes[:3]:
    nom = prod.find_element(By.CSS_SELECTOR, 'a.article-link div.text p').get_attribute('innerText').strip()
    preu = prod.find_element(By.CSS_SELECTOR, 'div.price span').get_attribute('innerText').strip()
    pes = prod.find_element(By.CSS_SELECTOR, 'div.weight').get_attribute('innerText').strip()
    # Busquem el preu per kg/l
    try:
        preu_unitari = prod.find_element(By.CSS_SELECTOR, 'div.price-per-unit').get_attribute('innerText').strip()
    except:
        preu_unitari = 'NO TROBAT'
    print(f"\n  Nom: {nom}")
    print(f"  Preu: {preu}")
    print(f"  Pes: {pes}")
    print(f"  Preu/unit: {preu_unitari}")

driver.quit()
