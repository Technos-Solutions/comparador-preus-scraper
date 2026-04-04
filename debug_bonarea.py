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

url_frescos = 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11'
slug_pare = 'frescos'

driver = crear_driver()
driver.get(url_frescos)
time.sleep(8)
for i in range(3):
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
    time.sleep(2)

links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
subcats = []
uuids_vistos = set()
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    uuid = href.split('/')[-1].split('?')[0]
    if uuid in uuids_vistos or not text or len(uuid) < 10:
        continue
    path = href.split('/categories/')[-1].split('?')[0]
    segments = [s for s in path.split('/') if s]
    if len(segments) >= 3 and slug_pare in path:
        uuids_vistos.add(uuid)
        subcats.append(text)

print(f'Subcategories de Frescos: {len(subcats)}')
for s in subcats:
    print(f'  ✅ {s}')
driver.quit()
