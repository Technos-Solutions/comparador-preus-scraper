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

categories_grans = [
    ('Verduras', 'https://www.dia.es/verduras/c/L104'),
    ('Limpieza', 'https://www.dia.es/limpieza-y-hogar/c/L122'),
    ('Charcuteria', 'https://www.dia.es/charcuteria-y-quesos/c/L101'),
]

for nom, url in categories_grans:
    driver = crear_driver()
    driver.get(url)
    time.sleep(8)
    links = driver.find_elements(By.TAG_NAME, 'a')
    subcats = set()
    for link in links:
        href = link.get_attribute('href') or ''
        if re.search(r'dia\.es/[^/]+/[^/]+/c/L\d+$', href):
            subcats.add(href)
    print(f'{nom}: {len(subcats)} subcategories')
    driver.quit()
