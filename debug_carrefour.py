from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

print("="*60)
print("🔍 DEBUG BON ÀREA - Anàlisi completa")
print("="*60)

def crear_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

url = 'https://www.bonarea-online.com/categories/lactics-i-derivats/13_300_080_010'
driver = crear_driver()

try:
    print(f"\n📡 Carregant: {url}")
    driver.get(url)
    print("⏳ Esperant 8 segons...")
    time.sleep(8)

    print(f"\n📄 Títol: {driver.title}")
    print(f"🔗 URL final: {driver.current_url}")

    # Scroll
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(1)

    # Provar selectors
    print("\n" + "="*60)
    print("🔍 PROVANT SELECTORS:")
    print("="*60)

    selectors = [
        'div.block-product',
        'a.article-link',
        'a.article-link div.text p',
        'div.price span',
        'div.price',
        'div.text p',
        'div.weight',
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"  '{selector}' → {len(elements)} elements")
            if elements:
                text = elements[0].get_attribute('innerText') or elements[0].text
                print(f"    → Primer element: '{text[:100]}'")
        except Exception as e:
            print(f"  '{selector}' → ERROR: {e}")

    # Mostrar primers 3 productes complets
    print("\n" + "="*60)
    print("🔍 PRIMERS 3 PRODUCTES COMPLETS:")
    print("="*60)
    productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
    print(f"Total productes trobats: {len(productes)}")
    for i, prod in enumerate(productes[:3]):
        print(f"\nProducte {i+1}:")
        print(f"  text: '{prod.get_attribute('innerText')[:200]}'")

except Exception as e:
    print(f"\n❌ Error general: {e}")
finally:
    driver.quit()
    print("\n✅ Driver tancat")
    print("="*60)
