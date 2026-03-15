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
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.binary_location = '/usr/bin/chromium-browser'
    from selenium.webdriver.chrome.service import Service
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

driver = crear_driver()
driver.get('https://www.dia.es/compra-online')
time.sleep(10)

print(f"📄 Títol: {driver.title}")
print(f"🔗 URL final: {driver.current_url}")

# Tots els links de la pàgina
print("\n🔍 TOTS ELS LINKS (primers 30):")
links = driver.find_elements(By.TAG_NAME, 'a')
print(f"Total links: {len(links)}")
for link in links[:30]:
    href = link.get_attribute('href')
    text = link.get_attribute('innerText').strip()[:50]
    if href and text:
        print(f"  {text} → {href}")

driver.quit()
