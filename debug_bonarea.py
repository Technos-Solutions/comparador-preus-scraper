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
nom_cat = 'mascotas'
codi_cat = 'cat20007'
max_productes = 100
count = 0
offset = 0
noms_anteriors = set()

while count < max_productes:
    driver = crear_driver()
    url = f'{base_url}/{nom_cat}/{codi_cat}/c?offset={offset}'
    driver.get(url)
    time.sleep(10)
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(2)
    noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')

    # Extreure text ABANS de tancar el driver
    noms_actuals = set(n.get_attribute('innerText').strip() for n in noms)
    driver.quit()

    if not noms_actuals:
        print(f"offset={offset} -> 0 productes, parant")
        break

    if noms_actuals == noms_anteriors:
        print(f"offset={offset} -> pagina repetida, parant!")
        break

    noms_anteriors = noms_actuals
    count += len(noms_actuals)
    print(f"offset={offset} -> {len(noms_actuals)} productes")
    offset += 24

print(f"Total: {count} productes")
