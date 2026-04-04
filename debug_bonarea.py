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
    chrome_options.add_argument('user-agent=Mozilla/5.0')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

# Carregem Verduras i trobem totes les subcategories
driver = crear_driver()
driver.get('https://www.dia.es/verduras/c/L104')
time.sleep(8)

print('SUBCATEGORIES DE VERDURAS:')
links = driver.find_elements(By.TAG_NAME, 'a')
total = 0
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    # Subcategories segueixen el patró /categoria/subcategoria/c/LXXXXX
    if re.search(r'dia\.es/[^/]+/[^/]+/c/L\d+$', href) and text:
        print(f'  {text} -> {href}')
        total += 1

print(f'\nTotal subcategories: {total}')
driver.quit()
