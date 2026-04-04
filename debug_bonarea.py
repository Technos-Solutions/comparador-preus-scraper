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

# Problema 1: totes les categories disponibles
driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat')
time.sleep(8)
links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
print(f'TOTES LES CATEGORIES TROBADES ({len(links)} links):')
vistos = set()
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    uuid = href.split('/')[-1].split('?')[0]
    if uuid not in vistos and text:
        vistos.add(uuid)
        print(f'  {text} -> {uuid[:20]}...')
driver.quit()

print('\n---')

# Problema 2: quants productes te realment Frescos?
driver = crear_driver()
url = 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11'
driver.get(url)
time.sleep(10)

anterior = 0
for i in range(20):
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
    time.sleep(3)
    actual = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
    print(f'Scroll {i+1}: {actual} productes')
    if actual == anterior and i > 2:
        print('No hi ha mes productes, parant')
        break
    anterior = actual

driver.quit()
