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

def decidir_estrategia(base_url, nom):
    # Comptem _001 i _010
    for suffix in ['_001', '_010']:
        driver = crear_driver()
        driver.get(base_url + suffix)
        time.sleep(6)
        p = len(driver.find_elements(By.CSS_SELECTOR, 'div.block-product'))
        driver.quit()
        if suffix == '_001': p001 = p
        if suffix == '_010': p010 = p

    # Regla: si _001 >= 3x _010, usar _001
    if p010 == 0 or p001 >= p010 * 3:
        estrategia = 'usar _001'
    else:
        estrategia = 'iterar _010, _020...'

    print(f'{nom}: _001={p001}, _010={p010} -> {estrategia}')

categories = [
    ('https://www.bonarea-online.com/categories/vi-blanc/13_320_090', 'Vi blanc'),
    ('https://www.bonarea-online.com/categories/begudes-refrescants/13_320_030', 'Refrescos'),
    ('https://www.bonarea-online.com/categories/lactics-i-derivats/13_300_080', 'Lactics'),
    ('https://www.bonarea-online.com/categories/conserves/13_300_040', 'Conserves'),
    ('https://www.bonarea-online.com/categories/carns-i-ous/13_300_010', 'Carns'),
]

for url, nom in categories:
    decidir_estrategia(url, nom)
