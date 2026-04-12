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

# Testem Congelats - subcategories de nivell 2
url_congelats = 'https://www.compraonline.bonpreuesclat.cat/categories/congelats/79a52e84-e446-47fb-b032-dfa044ecb779'

driver = crear_driver()
driver.get(url_congelats)
time.sleep(10)
for i in range(3):
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
    time.sleep(2)

links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
print('SUBCATEGORIES DE CONGELATS:')
uuids_vistos = set()
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    uuid = href.split('/')[-1].split('?')[0]
    if uuid in uuids_vistos or not text or len(uuid) < 10:
        continue
    if 'congelats' in href and '79a52e84' not in uuid:
        uuids_vistos.add(uuid)
        # Ara comprovem si aquesta subcategoria te productes o mes subcategories
        driver2 = crear_driver()
        driver2.get(href.split('?')[0])
        time.sleep(8)
        prods = driver2.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
        subcats_n3 = [l for l in driver2.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
                      if uuid[:8] in (l.get_attribute('href') or '')]
        driver2.quit()
        print(f'  {text}: {len(prods)} productes, {len(subcats_n3)} sub-subcategories')

driver.quit()
