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

categories = [
    ('Lactics i ous', 'https://www.compraonline.bonpreuesclat.cat/categories/lactics-i-ous/8e6bb6f8-67ac-4a57-8'),
    ('Cura personal', 'https://www.compraonline.bonpreuesclat.cat/categories/cura-personal/b2c9fc2f-ddb1-40ff-8'),
    ('Per la llar', 'https://www.compraonline.bonpreuesclat.cat/categories/per-la-llar/6ea50412-555a-4d5a-8'),
    ('Espai mascotes', 'https://www.compraonline.bonpreuesclat.cat/categories/espai-mascotes/503fab97-1ab4-48c4-b'),
    ('Parafarmacia', 'https://www.compraonline.bonpreuesclat.cat/categories/parafarmacia/402b37ee-e28d-42d0-8'),
]

for nom, url in categories:
    driver = crear_driver()
    driver.get(url)
    time.sleep(10)
    for i in range(5):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
    p = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
    print(f'{nom}: {p} productes')
    driver.quit()
