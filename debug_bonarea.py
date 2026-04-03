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

base = 'https://www.bonarea-online.com/categories/begudes-refrescants/13_320_030'
for n in range(1, 10):
    suffix = f'_{n*10:03d}'
    driver = crear_driver()
    driver.get(base + suffix)
    time.sleep(6)
    productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
    print(f'13_320_030{suffix} -> {len(productes)} productes')
    driver.quit()
    if not productes:
        break
