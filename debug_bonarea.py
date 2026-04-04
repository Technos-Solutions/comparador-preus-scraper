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

subcategories = [
    ('Formatgeria', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/formatges/c756085a-210c-4531-937a-46967fcc405e'),
    ('Xarcuteria', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/xarcuteria/5426a8b4-f65b-49ab-8058-1b3af4ba00a5'),
    ('Peixateria', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/peixateria/cfca08f2-5d86-4bab-bb4a-ba80cd5de82e'),
    ('Fruites i verdures', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/fruites-i-verdures/130716f2-795a-4f0b-ad39-b449817921b3'),
    ('Plats preparats', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/plats-preparats/c6a55f73-81e5-413b-bf7e-3f91f0949d92'),
]

for nom, url in subcategories:
    driver = crear_driver()
    driver.get(url)
    time.sleep(10)
    anterior = 0
    for i in range(10):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
        actual = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
        if actual == anterior and i > 2:
            break
        anterior = actual
    print(f'{nom}: {actual} productes')
    driver.quit()
