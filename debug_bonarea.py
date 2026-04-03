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
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

def convertir_pes(pes_text):
    match = re.match(r'([0-9.]+)(kg|l|g|ml)', pes_text.strip(), re.IGNORECASE)
    if not match:
        return pes_text
    val = float(match.group(1))
    unitat = match.group(2).lower()
    if unitat == 'kg':
        if val < 1:
            return f"{int(val*1000)} g"
        else:
            return f"{val} kg"
    elif unitat == 'l':
        if val < 1:
            return f"{int(val*1000)} ml"
        else:
            return f"{val} l"
    return pes_text

driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat/categories/alimentaci%C3%B3/c49d1ef2-bf51-44a7-b631-4a35474a21ac')
time.sleep(12)
for i in range(5):
    driver.execute_script("
