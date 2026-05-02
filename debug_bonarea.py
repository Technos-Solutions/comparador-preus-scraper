# Debug BonPreuEsclat - Verificar cookie language=es-ES
# Comprova que els productes surten amb nom primer (no marca primer)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

BASE_URL = 'https://www.compraonline.bonpreuesclat.cat'

def crear_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--single-process')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

print("=" * 60)
print("DEBUG: Cookie language=es-ES a BonPreuEsclat")
print("=" * 60)

driver = crear_driver()

try:
    print("\n1. Carregant pàgina principal...")
    driver.get(BASE_URL)
    time.sleep(5)

    print("2. Afegint cookie language=es-ES...")
    driver.add_cookie({
        "name": "language",
        "value": "es-ES",
        "domain": "www.compraonline.bonpreuesclat.cat"
    })
    driver.refresh()
    time.sleep(8)

    print("3. Descobrint categories...")
    links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
    url_prova = None
    for link in links:
        href = link.get_attribute('href') or ''
        text = link.get_attribute('innerText').strip().lower()
        if 'fresc' in text and '/categories/' in href:
            url_prova = href
            print(f"   Categoria trobada: {text} -> {href}")
            break

    if not url_prova:
        print("   ⚠️  No s'ha trobat categoria frescos, usant URL directa")
        url_prova = BASE_URL + '/categories/frescos'

    print(f"\n4. Extraient productes de: {url_prova}")
    driver.get(url_prova)
    time.sleep(6)
    for i in range(3):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(1)

    noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
    print(f"\n✅ {len(noms)} productes trobats. Primers 10:")
    print("-" * 50)
    for i, nom in enumerate(noms[:10]):
        print(f"  {i+1}. {nom.get_attribute('innerText').strip()}")

    print("\n" + "=" * 60)
    print("Comprova que el NOM va primer i la MARCA al final.")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print("\nDriver tancat.")
