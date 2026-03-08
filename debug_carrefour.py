from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

print("="*60)
print("🔍 DEBUG CARREFOUR - Anàlisi completa")
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
    print("⏳ Esperant 8 segons...")
    time.sleep(8)

    # Títol de la pàgina
    print(f"\n📄 Títol de la pàgina: {driver.title}")

    # URL final (per si hi ha redirecció)
    print(f"🔗 URL final: {driver.current_url}")

    # Primer tros del HTML
    print("\n" + "="*60)
    print("📝 PRIMERS 3000 CARÀCTERS DEL HTML:")
    print("="*60)
    print(driver.page_source[:3000])

    # Scroll
    print("\n⏳ Fent scrolls...")
    for i in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # Comptar elements amb diferents selectors
    print("\n" + "="*60)
    print("🔍 PROVANT SELECTORS:")
    print("="*60)

    selectors = [
        'a.product-card__title-link',
        'span.product-card__price',
        '.product-card',
        '.product-card__title',
        'h2.product-card__title',
        '[class*="product-card"]',
        '[class*="product"]',
        'article',
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"  '{selector}' → {len(elements)} elements trobats")
            if elements and len(elements) > 0:
                print(f"    → Text primer element: '{elements[0].text[:100]}'")
        except Exception as e:
            print(f"  '{selector}' → ERROR: {e}")

    # HTML després del scroll
    print("\n" + "="*60)
    print("📝 HTML DESPRÉS DEL SCROLL (primers 3000 caràcters):")
    print("="*60)
    print(driver.page_source[:3000])

except Exception as e:
    print(f"\n❌ Error general: {e}")

finally:
    driver.quit()
    print("\n✅ Driver tancat")
    print("="*60)
