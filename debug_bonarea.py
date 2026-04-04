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

# Entrem a Frescos i veiem totes les subcategories
driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11')
time.sleep(10)

links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
print('SUBCATEGORIES DE FRESCOS:')
vistos = set()
for link in links:
    href = link.get_attribute('href') or ''
    text = link.get_attribute('innerText').strip()
    uuid = href.split('/')[-1].split('?')[0]
    if uuid not in vistos and text and len(uuid) > 10:
        # Excloure la categoria pare
        if 'c95cfbf2' not in uuid:
            vistos.add(uuid)
            url_neta = f"https://www.compraonline.bonpreuesclat.cat/categories/{href.split('/categories/')[1].split('?')[0]}"
            print(f'  {text} -> {url_neta}')

print(f'\nTotal subcategories: {len(vistos)}')
driver.quit()
