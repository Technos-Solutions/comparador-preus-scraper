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

driver = crear_driver()
driver.get('https://www.carrefour.es/supermercado/frescos/cat20002/c')
time.sleep(12)
for i in range(5):
    driver.execute_script('window.scrollBy(0, 400)')
    time.sleep(2)

print(f'Titol: {driver.title}')
print(f'URL final: {driver.current_url}')

# Provem selectors alternatius
selectors = [
    'a.product-card__title-link',
    '[class*="product-card__title"]',
    '[class*="product-card"]',
    'article',
    '[data-testid*="product"]',
]
for sel in selectors:
    els = driver.find_elements(By.CSS_SELECTOR, sel)
    print(f'  {sel} -> {len(els)} elements')

# Veiem el HTML per entendre l estructura
print('\nHTML (primers 1000 chars del body):')
print(driver.find_element(By.TAG_NAME, 'body').get_attribute('innerHTML')[:1000])
driver.quit()
