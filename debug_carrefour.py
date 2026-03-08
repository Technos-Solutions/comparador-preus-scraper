from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

print("="*60)
print("🔍 DEBUG CARREFOUR v2 - Esperant contingut JS")
print("="*60)

def crear_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

url = 'https://www.carrefour.es/supermercado/frescos/cat20002/c'
driver = crear_driver()

try:
    print(f"\n📡 Carregant: {url}")
    driver.get(url)
    print("⏳ Esperant 10 segons per JS...")
    time.sleep(10)

    # Scroll per activar lazy loading
    print("⏳ Fent scrolls lents...")
    for i in range(5):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(2)

    # Esperar que algun element tingui text
    print("⏳ Esperant que els textos es carreguin...")
    time.sleep(5)

    # Provar de llegir el text dels elements
    print("\n" + "="*60)
    print("🔍 LLEGINT TEXT DELS PRIMERS 5 PRODUCTES:")
    print("="*60)

    noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')
    preus = driver.find_elements(By.CSS_SELECTOR, 'span.product-card__price')

    print(f"Noms trobats: {len(noms)}")
    print(f"Preus trobats: {len(preus)}")

    for i in range(min(5, len(noms))):
        nom_text = noms[i].text
        nom_inner = noms[i].get_attribute('innerHTML')
        nom_inner_text = noms[i].get_attribute('innerText')
        print(f"\nProducte {i+1}:")
        print(f"  .text → '{nom_text}'")
        print(f"  innerText → '{nom_inner_text}'")
        print(f"  innerHTML → '{nom_inner[:200]}'")

    print("\n" + "="*60)
    print("🔍 LLEGINT TEXT DELS PRIMERS 5 PREUS:")
    print("="*60)
    for i in range(min(5, len(preus))):
        preu_text = preus[i].text
        preu_inner = preus[i].get_attribute('innerText')
        print(f"Preu {i+1}: .text='{preu_text}' | innerText='{preu_inner}'")

    # Mirar si .product-card té text
    print("\n" + "="*60)
    print("🔍 TEXT DE .product-card:")
    print("="*60)
    cards = driver.find_elements(By.CSS_SELECTOR, '.product-card')
    for i in range(min(3, len(cards))):
        print(f"\nCard {i+1}: '{cards[i].text[:300]}'")

except Exception as e:
    print(f"\n❌ Error general: {e}")
finally:
    driver.quit()
    print("\n✅ Driver tancat")
