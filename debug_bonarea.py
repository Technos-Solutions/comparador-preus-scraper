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

# Carreguem la categoria de vins i veiem quines subcategories apareixen al menú
driver = crear_driver()
driver.get('https://www.bonarea-online.com/categories/vi-blanc/13_320_090')
time.sleep(8)

print('URLs de subcategories trobades:')
links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    codi = href.split('/')[-1]
    if codi.startswith('13_320_090') and codi.count('_') >= 3:
        print(f'  {text} -> {codi}')

driver.quit()
