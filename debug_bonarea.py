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

# Testem "Tot en X" per les 3 categories grans
categories = [
    ('Frescos', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11'),
    ('Alimentació', 'https://www.compraonline.bonpreuesclat.cat/categories/alimentaci%C3%B3/c49d1ef2-bf51-44a7-b631-4a35474a21ac'),
    ('Begudes', 'https://www.compraonline.bonpreuesclat.cat/categories/begudes/3660db45-baa3-4c9f-9bb1-7cba443b3c9f'),
]

for nom, url in categories:
    inici = time.time()
    driver = crear_driver()
    driver.get(url)
    time.sleep(5)

    anterior = 0
    for i in range(30):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
        actual = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
        print(f'  {nom} scroll {i+1}: {actual} productes')
        if actual == anterior and i > 2:
            break
        anterior = actual

    elapsed = time.time() - inici
    print(f'✅ {nom}: {actual} productes en {elapsed:.0f}s ({elapsed/60:.1f} min)\n')
    driver.quit()
