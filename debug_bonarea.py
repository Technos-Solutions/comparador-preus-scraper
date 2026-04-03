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

urls = [
    ('Vi blanc _001 (tots)', 'https://www.bonarea-online.com/categories/tots-els-vins-blancs/13_320_090_001'),
    ('Vi blanc _010 (DO Segre)', 'https://www.bonarea-online.com/categories/do-costers-del-segre/13_320_090_010'),
    ('Refrescos _001', 'https://www.bonarea-online.com/categories/begudes-refrescants/13_320_030_001'),
    ('Refrescos _010', 'https://www.bonarea-online.com/categories/begudes-refrescants/13_320_030_010'),
]

for nom, url in urls:
    driver = crear_driver()
    driver.get(url)
    time.sleep(6)
    productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
    print(f'{nom} -> {len(productes)} productes')
    driver.quit()
