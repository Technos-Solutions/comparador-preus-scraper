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

url = 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11?sortBy=favorite'

driver = crear_driver()
print(f"📡 Carregant: {url}")
driver.get(url)
time.sleep(10)

for i in range(5):
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(2)

print(f"📄 Títol: {driver.title}")

noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
preus = driver.find_elements(By.CSS_SELECTOR, 'span[data-test="fop-price"]')

print(f"\n🔍 Noms trobats: {len(noms)}")
print(f"🔍 Preus trobats: {len(preus)}")

for i in range(min(5, len(noms), len(preus))):
    nom = noms[i].get_attribute('innerText').strip()
    preu = preus[i].get_attribute('innerText').strip()
    print(f"  {nom} → {preu}")

driver.quit()
