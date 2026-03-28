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

base_url = 'https://www.carrefour.es/supermercado'
categories = [
    ('bebe', 'cat20006'),
    ('mascotas', 'cat20007'),
]

for nom_cat, codi_cat in categories:
    print(f"\nCategoria: {nom_cat}")
    time.sleep(10)
    driver = crear_driver()
    url = f'{base_url}/{nom_cat}/{codi_cat}/c?offset=0'
    driver.get(url)
    time.sleep(10)
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(2)
    noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')
    noms_text = [n.get_attribute('innerText').strip() for n in noms]
    driver.quit()
    print(f"  Productes: {len(noms_text)}")
    if noms_text:
        print(f"  Primer: {noms_text[0]}")
