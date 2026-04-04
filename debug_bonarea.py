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
    chrome_options.add_argument('user-agent=Mozilla/5.0')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

# Comprovem 3 subcategories de Verduras
urls = [
    ('Lechugas', 'https://www.dia.es/verduras/lechugas-y-hojas-verdes/c/L2027'),
    ('Tomates', 'https://www.dia.es/verduras/tomates-pimientos-y-pepinos/c/L2023'),
    ('Conservas verduras', 'https://www.dia.es/verduras/conservas-de-verduras/c/L2026'),
]

for nom, url in urls:
    driver = crear_driver()
    noms_anteriors = set()
    total = 0
    for pagina in range(10):
        driver.get(f'{url}?q=%3Arelevance&pageSize=48&currentPage={pagina}')
        time.sleep(6)
        cards = driver.find_elements(By.CSS_SELECTOR, '.search-product-card')
        if not cards:
            break
        noms = set()
        for card in cards:
            try:
                n = card.find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-name"]').get_attribute('innerText').strip()
                noms.add(n)
            except:
                pass
        if noms == noms_anteriors:
            break
        total += len(cards)
        noms_anteriors = noms
    print(f'{nom}: {total} productes')
    driver.quit()
