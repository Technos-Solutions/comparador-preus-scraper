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

def get_subcategories(driver, url):
    path_pare = url.split('/categories/')[-1].split('?')[0]
    segments_pare = [s for s in path_pare.split('/') if s]
    slug_pare = segments_pare[0]
    n_segments_pare = len(segments_pare)
    links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
    subcats = []
    uuids_vistos = set()
    for link in links:
        href = link.get_attribute('href') or ''
        text = link.get_attribute('innerText').strip()
        if '/categories/' not in href or not text:
            continue
        path = href.split('/categories/')[-1].split('?')[0]
        segments = [s for s in path.split('/') if s]
        uuid = segments[-1] if segments else ''
        if (len(segments) == n_segments_pare + 1
                and segments[0] == slug_pare
                and len(uuid) > 10
                and uuid not in uuids_vistos):
            uuids_vistos.add(uuid)
            subcats.append((text, f"https://www.compraonline.bonpreuesclat.cat/categories/{path}"))
    return subcats

# Mesurem NOMÉS la categoria Congelats
inici = time.time()
nodes_visitats = [0]
productes_totals = [0]

def scrape_recursiu(url, driver, nivell=0):
    nodes_visitats[0] += 1
    driver.get(url)
    time.sleep(5)
    for i in range(2):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
    subcats = get_subcategories(driver, url)
    nom = url.split('/')[-2]
    if subcats:
        print(f"{'  '*nivell}📂 {nom}: {len(subcats)} subcats")
        for _, url_sub in subcats:
            scrape_recursiu(url_sub, driver, nivell+1)
    else:
        driver.get(url)
        time.sleep(4)
        for i in range(5):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            prods = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
            if len(prods) == productes_totals[0] and i > 1:
                break
        prods = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
        productes_totals[0] += len(prods)
        print(f"{'  '*nivell}└ {nom}: {len(prods)} productes")

driver = crear_driver()
scrape_recursiu('https://www.compraonline.bonpreuesclat.cat/categories/congelats/79a52e84-e446-47fb-b032-dfa044ecb779', driver)
driver.quit()

elapsed = time.time() - inici
print(f'\n⏱️ Congelats: {elapsed:.0f}s ({elapsed/60:.1f} min)')
print(f'📦 Nodes visitats: {nodes_visitats[0]}')
print(f'🛒 Productes: {productes_totals[0]}')
print(f'⏱️ Temps per node: {elapsed/nodes_visitats[0]:.1f}s')
print(f'\n📊 Estimació 11 categories: {elapsed/60*11:.0f} min ({elapsed/60*11/60:.1f}h)')
