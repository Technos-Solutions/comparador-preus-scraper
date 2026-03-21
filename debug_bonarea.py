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

# Provem una URL que dona 0 i una que funciona
urls = [
    'https://www.bonarea-online.com/categories/lactics-i-derivats/13_300_080',
    'https://www.bonarea-online.com/categories/lleixius-i-desinfectants/13_330_080',
]

for url in urls:
    driver = crear_driver()
    print(f"\n📡 Provant: {url}")
    driver.get(url)
    time.sleep(10)
    print(f"  URL final: {driver.current_url}")
    productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
    print(f"  Productes: {len(productes)}")
    if productes:
        print(f"  Primer: {productes[0].get_attribute('innerText')[:60]}")
    driver.quit()
