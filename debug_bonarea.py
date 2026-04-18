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

BASE = 'https://www.compraonline.bonpreuesclat.cat'

def get_subcategories(driver, url):
    # El slug pare es el PRIMER segment (no el UUID)
    path_pare = url.split('/categories/')[-1].split('?')[0]
    segments_pare = [s for s in path_pare.split('/') if s]
    slug_pare = segments_pare[0]  # ex: 'congelats', 'frescos'
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
        # Subcategoria directa: comenca amb el slug pare i te 1 segment mes
        if (len(segments) == n_segments_pare + 1
                and segments[0] == slug_pare
                and len(uuid) > 10
                and uuid not in uuids_vistos):
            uuids_vistos.add(uuid)
            subcats.append((text, BASE + '/categories/' + path))
    return subcats

def descobrir_recursiu(url, nivell=0):
    prefix = '  ' * nivell
    driver = crear_driver()
    driver.get(url)
    time.sleep(8)
    for i in range(5):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
    prods = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
    subcats = get_subcategories(driver, url)
    driver.quit()

    nom = url.split('/')[-2]
    if subcats:
        print(f'{prefix}[N{nivell}] {nom}: {len(subcats)} subcategories')
        for nom_sub, url_sub in subcats:
            descobrir_recursiu(url_sub, nivell+1)
    else:
        print(f'{prefix}[N{nivell}] {nom}: {len(prods)} productes')

for nom, url in [
    ('Congelats', 'https://www.compraonline.bonpreuesclat.cat/categories/congelats/79a52e84-e446-47fb-b032-dfa044ecb779'),
    ('Frescos', 'https://www.compraonline.bonpreuesclat.cat/categories/frescos/c95cfbf2-501d-433f-bae3-10fcef330b11'),
]:
    print(f'\n=== {nom} ===')
    descobrir_recursiu(url)
