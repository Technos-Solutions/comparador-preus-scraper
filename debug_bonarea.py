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

def trobar_suffix(base_url):
    suffixos = ['', '_010', '_020', '_030', '_040', '_050',
                '_001', '_002', '_003', '_004', '_005']
    for suffix in suffixos:
        driver = crear_driver()
        url = base_url + suffix
        driver.get(url)
        time.sleep(6)
        productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
        driver.quit()
        if productes:
            print(f'OK: {base_url.split("/")[-1]}{suffix} -> {len(productes)} productes')
            return
    print(f'ERROR: {base_url.split("/")[-1]} -> cap suffix funciona')

categories_test = [
    'https://www.bonarea-online.com/categories/begudes-refrescants/13_320_030',
    'https://www.bonarea-online.com/categories/vi-blanc/13_320_090',
    'https://www.bonarea-online.com/categories/lactics-i-derivats/13_300_080',
]

for url in categories_test:
    trobar_suffix(url)
