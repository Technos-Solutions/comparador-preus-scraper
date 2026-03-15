from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re

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
driver.get('https://www.dia.es/frutas/c/L105')
time.sleep(10)

print(f"📄 Títol: {driver.title}")
print(f"🔗 URL final: {driver.current_url}")

print("\n🔍 CATEGORIES (patró /c/L):")
links = driver.find_elements(By.TAG_NAME, 'a')
vistos = set()
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    if re.search(r'/c/L\d+', href) and href not in vistos and text:
        vistos.add(href)
        print(f"  {text} → {href}")

print(f"\nTotal: {len(vistos)}")

# Productes a la categoria fruitas
cards = driver.find_elements(By.CSS_SELECTOR, '.search-product-card')
print(f"\n🛒 Productes a frutas: {len(cards)}")
if cards:
    nom = cards[0].find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-name"]').get_attribute('innerText')
    print(f"  Primer: {nom}")

driver.quit()
