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

driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11')
time.sleep(5)

anterior = 0
passos_sense_canvi = 0
for i in range(200):
    # Scroll gradual de 500px cada vegada
    driver.execute_script('window.scrollBy(0, 500)')
    time.sleep(0.5)
    actual = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
    if actual != anterior:
        print(f'  scroll {i+1}: {actual} productes')
        anterior = actual
        passos_sense_canvi = 0
    else:
        passos_sense_canvi += 1
        if passos_sense_canvi > 10:
            print(f'  -> FI: {actual} productes')
            break

driver.quit()
