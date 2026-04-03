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

def comptar_subcategories(base_url, nom):
    print(f'\n{nom}:')
    total = 0
    # Provar _001 primer
    driver = crear_driver()
    driver.get(base_url + '_001')
    time.sleep(6)
    p001 = len(driver.find_elements(By.CSS_SELECTOR, 'div.block-product'))
    driver.quit()
    print(f'  _001 -> {p001} productes')

    # Provar _010, _020...
    for n in range(1, 15):
        suffix = f'_{n*10:03d}'
        driver = crear_driver()
        driver.get(base_url + suffix)
        time.sleep(6)
        p = len(driver.find_elements(By.CSS_SELECTOR, 'div.block-product'))
        driver.quit()
        print(f'  {suffix} -> {p} productes')
        if p == 0:
            break
        total += p

    print(f'  TOTAL iterant _010... = {total}')

comptar_subcategories(
    'https://www.bonarea-online.com/categories/vi-blanc/13_320_090',
    'Vi blanc'
)
comptar_subcategories(
    'https://www.bonarea-online.com/categories/begudes-refrescants/13_320_030',
    'Refrescos'
)
