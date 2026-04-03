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
driver.get('https://www.bonarea-online.com/categories/vi-blanc/13_320_090_001')
time.sleep(10)

print('TOTS ELS LINKS /categories/ de la pagina:')
links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
print(f'Total: {len(links)}')
for link in links[:30]:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()[:40]
    codi = href.split('/')[-1]
    print(f'  {codi} | {text}')

driver.quit()
