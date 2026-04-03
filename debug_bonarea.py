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

def extreure_quantitat(nom):
    # Cerca la ULTIMA ocurrencia de quantitat al nom
    matches = re.findall(r'(\d+[.,]?\d*)\s*(kg|g|l|ml|cl|ud|unidades?)', nom, re.IGNORECASE)
    if matches:
        val, unitat = matches[-1]
        return f"{val} {unitat.lower()}"
    return ''

driver = crear_driver()
driver.get('https://www.carrefour.es/supermercado/frescos/cat20002/c?offset=0')
time.sleep(10)
for i in range(3):
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(2)

noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')
print(f"{'Nom':<55} {'Quantitat':<15}")
print("-"*70)
for nom_el in noms[:10]:
    nom = nom_el.get_attribute('innerText').strip()
    quantitat = extreure_quantitat(nom)
    print(f"{nom[:55]:<55} {quantitat:<15}")

driver.quit()
