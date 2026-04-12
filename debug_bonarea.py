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

def descobrir_recursiu(url, nivell=0, max_nivell=3):
    """Descobreix recursivament totes les subcategories i compta productes"""
    prefix = '  ' * nivell
    driver = crear_driver()
    driver.get(url)
    time.sleep(8)
    for i in range(5):
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)

    # Productes a aquesta pagina
    prods = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
    n_prods = len(prods)

    # Subcategories d'aquesta pagina
    links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
    uuid_actual = url.split('/')[-1].split('?')[0]
    subcats = []
    uuids_vistos = set()
    for link in links:
        href = link.get_attribute('href') or ''
        text = link.get_attribute('innerText').strip()
        uuid = href.split('/')[-1].split('?')[0]
        # Subcategoria: ha de contenir el path de l'actual i ser diferent
        path_actual = url.split('/categories/')[-1].split('?')[0]
        path_link = href.split('/categories/')[-1].split('?')[0] if '/categories/' in href else ''
        if (uuid not in uuids_vistos and text and len(uuid) > 10
                and uuid != uuid_actual
                and path_actual in path_link
                and path_link != path_actual):
            uuids_vistos.add(uuid)
            url_neta = BASE + '/categories/' + path_link
            subcats.append((text, url_neta))

    driver.quit()

    if subcats and nivell < max_nivell:
        print(f'{prefix}[N{nivell}] {url.split("/")[-2]}: {len(subcats)} subcategories')
        for nom, url_sub in subcats:
            descobrir_recursiu(url_sub, nivell+1, max_nivell)
    else:
        print(f'{prefix}[N{nivell}] {url.split("/")[-2]}: {n_prods} productes FINALS')

# Testem amb Congelats
descobrir_recursiu('https://www.compraonline.bonpreuesclat.cat/categories/congelats/79a52e84-e446-47fb-b032-dfa044ecb779')
