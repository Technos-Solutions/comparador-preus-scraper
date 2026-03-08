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

driver = crear_driver()
driver.get('https://www.bonarea-online.com/ca/shop/shopping')
time.sleep(6)

print("🔍 CERCANT URLS DE CATEGORIES:")
links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
for link in links:
    href = link.get_attribute('href')
    text = link.get_attribute('innerText').strip()
    if href and text:
        print(f"  {text} → {href}")

driver.quit()
