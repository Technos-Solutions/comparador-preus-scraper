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
    ('Lechugas', 'https://www.dia.es/verduras/lechugas-y-hojas-verdes/c/L2027'),
    ('Tomates', 'https://www.dia.es/verduras/tomates-pimientos-y-pepinos/c/L2023'),
    ('Limpieza (categoria gran)', 'https://www.dia.es/limpieza-y-hogar/c/L122'),
]

for nom, url in urls:
    driver = crear_driver()
    driver.get(url)
    time.sleep(8)
    # Scroll per carregar tots
    anterior = 0
    for i in range(10):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
        actual = len(driver.find_elements(By.CSS_SELECTOR, '.search-product-card'))
        if actual == anterior and i > 1:
            break
        anterior = actual
    print(f'{nom}: {actual} productes')
    driver.quit()
