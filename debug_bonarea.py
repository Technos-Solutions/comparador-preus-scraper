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

url_base = 'https://www.dia.es/limpieza-y-hogar/c/L122'
noms_anteriors = set()
for pagina in range(30):
    driver = crear_driver()
    url = f'{url_base}?q=%3Arelevance&pageSize=48&currentPage={pagina}'
    driver.get(url)
    time.sleep(8)
    cards = driver.find_elements(By.CSS_SELECTOR, '.search-product-card')
    if not cards:
        print(f'pagina {pagina} -> 0 productes, FI')
        driver.quit()
        break
    # Extreure noms per detectar repeticio
    noms = set()
    for card in cards:
        try:
            nom = card.find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-name"]').get_attribute('innerText').strip()
            noms.add(nom)
        except:
            pass
    driver.quit()
    if noms == noms_anteriors:
        print(f'pagina {pagina} -> PAGINA REPETIDA, FI')
        break
    print(f'pagina {pagina} -> {len(cards)} productes')
    noms_anteriors = noms
