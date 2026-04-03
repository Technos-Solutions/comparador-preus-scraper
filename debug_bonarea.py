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

def convertir_pes(pes_text):
    match = re.match(r'([0-9.]+)(kg|l|g|ml)', pes_text.strip(), re.IGNORECASE)
    if not match:
        return pes_text
    val = float(match.group(1))
    unitat = match.group(2).lower()
    if unitat == 'kg':
        if val < 1:
            return str(int(val*1000)) + ' g'
        return str(val) + ' kg'
    elif unitat == 'l':
        if val < 1:
            return str(int(val*1000)) + ' ml'
        return str(val) + ' l'
    return pes_text

driver = crear_driver()
driver.get('https://www.compraonline.bonpreuesclat.cat/categories/alimentaci%C3%B3/c49d1ef2-bf51-44a7-b631-4a35474a21ac')
time.sleep(12)
driver.execute_script('window.scrollBy(0, 2000)')
time.sleep(5)

noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
preus = driver.find_elements(By.CSS_SELECTOR, 'span[data-test="fop-price"]')
print('Producte | Quantitat | Preu')
print('-'*60)
for i in range(min(10, len(noms))):
    nom = noms[i].get_attribute('innerText').strip()
    preu = preus[i].get_attribute('innerText').strip() if i < len(preus) else ''
    try:
        contenidor = noms[i].find_element(By.XPATH, '../../../..')
        pes_el = contenidor.find_element(By.CSS_SELECTOR, 'span[class*="weight"]')
        quantitat = convertir_pes(pes_el.get_attribute('innerText').strip())
    except:
        quantitat = ''
    print(nom[:40] + ' | ' + quantitat + ' | ' + preu)

driver.quit()
