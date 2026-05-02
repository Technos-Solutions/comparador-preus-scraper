import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime
import time

# Importacions Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("="*60)
print(f"🚀 SCRAPER INICIAT - {datetime.now()}")
print("="*60)

try:
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise Exception("⚠️ GOOGLE_CREDENTIALS no trobat!")
    creds_dict = json.loads(creds_json)
    print("✅ Credencials carregades correctament")
except Exception as e:
    print(f"❌ Error carregant credencials: {e}")
    exit(1)

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
print("✅ Connectat a Google Sheets")


class GoogleSheetsDB:
    def __init__(self, sheet):
        self.sheet = sheet

    def guardar_preus(self, preus_list):
        if not preus_list:
            print("⚠️ No hi ha preus per guardar")
            return
        ws = self.sheet.worksheet('Preus')
        for preu in preus_list:
            preu['data'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        try:
            existing = ws.get_all_values()
            last_id = len(existing) - 1 if len(existing) > 1 else 0
        except:
            last_id = 0
        rows = []
        for i, preu in enumerate(preus_list, start=1):
            row = [
                last_id + i,
                preu.get('producte', ''),
                preu.get('marca', ''),
                preu.get('supermercat', ''),
                preu.get('preu', 0),
                preu.get('quantitat', ''),
                preu.get('envas', ''),
                preu.get('data', '')
            ]
            rows.append(row)
        ws.append_rows(rows)
        print(f"✅ {len(preus_list)} preus guardats a Google Sheets!")


class MercadonaScraper:
    def __init__(self):
        self.base_url = 'https://tienda.mercadona.es/api'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'es-ES'
        }

    def calcular_quantitat(self, pi):
        unit_size = pi.get('unit_size', 0)
        size_format = pi.get('size_format', '')
        if size_format == 'kg':
            if unit_size < 1:
                return f"{int(unit_size*1000)} g"
            else:
                val = int(unit_size) if unit_size == int(unit_size) else unit_size
                return f"{val} kg"
        elif size_format == 'l':
            if unit_size < 1:
                return f"{int(unit_size*1000)} ml"
            else:
                val = int(unit_size) if unit_size == int(unit_size) else unit_size
                return f"{val} l"
        else:
            return f"{unit_size} {size_format}".strip()

    def scrape_all(self):
        print(f"\n🟢 Mercadona: extraient productes via API...")
        import requests
        productes = []
        try:
            url_cats = f'{self.base_url}/categories/?lang=es&wh=mad1'
            cats = requests.get(url_cats, headers=self.headers).json()
            for cat in cats.get('results', []):
                for subcat in cat.get('categories', []):
                    try:
                        url_sub = f"{self.base_url}/categories/{subcat['id']}/?lang=es&wh=mad1"
                        sub_data = requests.get(url_sub, headers=self.headers).json()
                        for sub2 in sub_data.get('categories', []):
                            for prod in sub2.get('products', []):
                                try:
                                    pi = prod['price_instructions']
                                    productes.append({
                                        'producte': prod['display_name'],
                                        'marca': prod.get('brand') or 'Hacendado',
                                        'supermercat': 'Mercadona',
                                        'preu': float(pi['unit_price']),
                                        'quantitat': self.calcular_quantitat(pi),
                                        'envas': prod.get('packaging') or ''
                                    })
                                except:
                                    continue
                        time.sleep(0.2)
                    except:
                        continue
        except Exception as e:
            print(f"  ❌ Error Mercadona: {e}")
        print(f"✅ Mercadona: {len(productes)} productes extrets")
        return productes


class DiaScraper:
    def __init__(self):
        self.base_url = 'https://www.dia.es'
        self.productes = []
        self.excloure = ['freidora-de-aire', 'sin-gluten', 'ofertas', 'recetas']

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        import re
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def descobrir_categories(self, driver):
        import re
        print("  🔍 Descobrint categories principals...")
        driver.get(f'{self.base_url}/frutas/c/L105')
        time.sleep(8)
        links = driver.find_elements(By.TAG_NAME, 'a')
        categories = []
        vistos = set()
        for link in links:
            href = link.get_attribute('href') or ''
            text = link.get_attribute('innerText').strip()
            match = re.search(r'dia\.es/([^/]+)/c/L(\d+)$', href)
            if match and href not in vistos and text:
                nom_cat = match.group(1)
                if not any(excl in nom_cat for excl in self.excloure):
                    vistos.add(href)
                    categories.append((text, href))
        print(f"  ✅ {len(categories)} categories principals trobades")
        return categories

    def descobrir_subcategories(self, driver, url_categoria):
        import re
        driver.get(url_categoria)
        time.sleep(8)
        links = driver.find_elements(By.TAG_NAME, 'a')
        subcats = []
        vistos = set()
        for link in links:
            href = link.get_attribute('href') or ''
            text = link.get_attribute('innerText').strip().replace('\nVer todos', '').strip()
            if re.search(r'dia\.es/[^/]+/[^/]+/c/L\d+$', href) and href not in vistos and text:
                vistos.add(href)
                subcats.append((text, href))
        return subcats

    def scrape_subcategoria(self, driver, nom, url):
        import re
        def extreure_quantitat(nom):
            match_pack = re.search(r'(\d+)\s*x\s*(\d+[.,]?\d*)\s*(kg|g|l|ml|cl)', nom, re.IGNORECASE)
            if match_pack:
                return f"{match_pack.group(1)} x {match_pack.group(2)} {match_pack.group(3).lower()}"
            matches = re.findall(r'(\d+[.,]?\d*)\s*(kg|g|l|ml|cl|ud|unidades?)', nom, re.IGNORECASE)
            if matches:
                val, unitat = matches[-1]
                return f"{val} {unitat.lower()}"
            return ''

        count = 0
        try:
            driver.get(url)
            time.sleep(8)
            anterior = 0
            for i in range(10):
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)
                actual = len(driver.find_elements(By.CSS_SELECTOR, '.search-product-card'))
                if actual == anterior and i > 1:
                    break
                anterior = actual

            cards = driver.find_elements(By.CSS_SELECTOR, '.search-product-card')
            for card in cards:
                try:
                    nom_prod = card.find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-name"]').get_attribute('innerText').strip()
                    preu_text = card.find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-unit-price"]').get_attribute('innerText')
                    preu_text = preu_text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                    preu = float(preu_text)
                    if nom_prod and preu > 0:
                        self.productes.append({'producte': nom_prod, 'marca': 'Día', 'supermercat': 'Dia', 'preu': preu, 'quantitat': extreure_quantitat(nom_prod), 'envas': ''})
                        count += 1
                except:
                    continue
        except Exception as e:
            print(f"      ❌ Error: {e}")
        return count

    def scrape_all(self, max_per_categoria=100):
        print("\n🟣 Dia: extraient productes amb Selenium...")
        driver_descobrir = None
        categories = []
        try:
            driver_descobrir = self._crear_driver()
            categories = self.descobrir_categories(driver_descobrir)
        except Exception as e:
            print(f"  ❌ Error descobrint categories: {e}")
        finally:
            if driver_descobrir:
                try:
                    driver_descobrir.quit()
                except:
                    pass

        for nom_cat, url_cat in categories:
            print(f"  📂 Categoria: {nom_cat}")
            driver_sub = None
            subcats = []
            try:
                driver_sub = self._crear_driver()
                subcats = self.descobrir_subcategories(driver_sub, url_cat)
            except Exception as e:
                print(f"    ❌ Error descobrint subcategories: {e}")
            finally:
                if driver_sub:
                    try:
                        driver_sub.quit()
                    except:
                        pass

            if subcats:
                print(f"    {len(subcats)} subcategories trobades")
                for nom_sub, url_sub in subcats:
                    driver = None
                    try:
                        driver = self._crear_driver()
                        count = self.scrape_subcategoria(driver, nom_sub, url_sub)
                        print(f"      └ {nom_sub}: {count} productes")
                    except Exception as e:
                        print(f"      └ ❌ Error {nom_sub}: {e}")
                    finally:
                        if driver:
                            try:
                                driver.quit()
                            except:
                                pass
                    time.sleep(1)
            else:
                driver = None
                try:
                    driver = self._crear_driver()
                    count = self.scrape_subcategoria(driver, nom_cat, url_cat)
                    print(f"    ✅ {count} productes extrets")
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
            time.sleep(2)

        print(f"✅ Dia: {len(self.productes)} productes extrets")
        return self.productes


class BonAreaScraper:
    def __init__(self):
        self.base_url = 'https://www.bonarea-online.com'
        self.productes = []
        self.codis_valids = ['13_300', '13_310', '13_320', '13_330', '13_340', '13_350', '13_030']

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def descobrir_categories(self, driver):
        print("  🔍 Descobrint categories automàticament...")
        driver.get(f'{self.base_url}/ca/shop/shopping')
        time.sleep(6)
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
        categories = []
        vistos = set()
        for link in links:
            href = link.get_attribute('href')
            if not href or href in vistos:
                continue
            vistos.add(href)
            codi = href.split('/')[-1]
            if any(codi.startswith(c) for c in self.codis_valids) and codi.count('_') >= 2:
                categories.append(href)
        print(f"  ✅ {len(categories)} categories trobades")
        return categories

    def extreure_productes(self, productes_elements):
        extrets = []
        for prod in productes_elements:
            try:
                nom = prod.find_element(By.CSS_SELECTOR, 'a.article-link div.text p').get_attribute('innerText').strip()
                preu_text = prod.find_element(By.CSS_SELECTOR, 'div.price span').get_attribute('innerText')
                preu_text = preu_text.replace('€/u.', '').replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                preu = float(preu_text)
                quantitat = prod.find_element(By.CSS_SELECTOR, 'div.weight').get_attribute('innerText').strip()
                if nom and preu > 0:
                    extrets.append({'producte': nom, 'marca': 'bonÀrea', 'supermercat': 'Bon Àrea', 'preu': preu, 'quantitat': quantitat, 'envas': ''})
            except:
                continue
        return extrets

    def scrape_categoria(self, driver, url):
        nom_cat = url.split('/')[-2]
        print(f"  📂 Categoria: {nom_cat}")
        count = 0
        try:
            driver.get(url + '_001')
            time.sleep(8)
            for i in range(3):
                driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(1)
            p001 = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
            n001 = len(p001)

            driver.get(url + '_010')
            time.sleep(8)
            for i in range(3):
                driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(1)
            p010 = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
            n010 = len(p010)

            if n010 == 0 or (n001 > 0 and n001 >= n010 * 3):
                print(f"    Estrategia: usar _001 ({n001} productes)")
                driver.get(url + '_001')
                time.sleep(8)
                for i in range(3):
                    driver.execute_script("window.scrollBy(0, 400);")
                    time.sleep(1)
                p001_fresh = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
                extrets = self.extreure_productes(p001_fresh)
                self.productes.extend(extrets)
                count += len(extrets)
            else:
                print(f"    Estrategia: iterar subcategories (_010, _020...)")
                extrets = self.extreure_productes(p010)
                self.productes.extend(extrets)
                count += len(extrets)
                for n in range(2, 30):
                    suffix = f'_{n*10:03d}'
                    driver.get(url + suffix)
                    time.sleep(6)
                    for i in range(3):
                        driver.execute_script("window.scrollBy(0, 400);")
                        time.sleep(1)
                    productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')
                    if not productes:
                        break
                    extrets = self.extreure_productes(productes)
                    self.productes.extend(extrets)
                    count += len(extrets)

            print(f"    ✅ {count} productes extrets")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        return count

    def scrape_all(self, max_productes=999):
        print(f"\n🟠 Bon Àrea: extraient productes amb Selenium...")
        driver_descobrir = None
        categories = []
        try:
            driver_descobrir = self._crear_driver()
            categories = self.descobrir_categories(driver_descobrir)
        except Exception as e:
            print(f"  ❌ Error descobrint categories: {e}")
        finally:
            if driver_descobrir:
                try:
                    driver_descobrir.quit()
                except:
                    pass

        for url in categories:
            driver = None
            try:
                driver = self._crear_driver()
                self.scrape_categoria(driver, url)
            except Exception as e:
                print(f"  ❌ Error general categoria: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            time.sleep(2)
        print(f"✅ Bon Àrea: {len(self.productes)} productes extrets")
        return self.productes


class CarrefourScraper:
    def __init__(self):
        self.base_url = 'https://www.carrefour.es/supermercado'
        self.productes = []
        self.categories = [
            ('frescos', 'cat20002'),
            ('la-despensa', 'cat20001'),
            ('bebidas', 'cat20003'),
            ('drogueria-y-limpieza', 'cat20005'),
            ('perfumeria-e-higiene', 'cat20004'),
            ('congelados', 'cat21449123'),
            ('bebe', 'cat20006'),
            ('mascotas', 'cat20007'),
        ]

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def scrape_pagina(self, driver, url):
        import re
        def extreure_quantitat(nom):
            matches = re.findall(r'(\d+[.,]?\d*)\s*(kg|g|l|ml|cl|ud|unidades?)', nom, re.IGNORECASE)
            if matches:
                val, unitat = matches[-1]
                return f"{val} {unitat.lower()}"
            return ''

        driver.get(url)
        time.sleep(10)
        for i in range(3):
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(2)
        noms = driver.find_elements(By.CSS_SELECTOR, 'a.product-card__title-link')
        preus = driver.find_elements(By.CSS_SELECTOR, 'span.product-card__price')
        productes = []
        for i in range(min(len(noms), len(preus))):
            try:
                nom = noms[i].get_attribute('innerText').strip()
                preu_text = preus[i].get_attribute('innerText').strip()
                if not nom or not preu_text:
                    continue
                preu_text = preu_text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                preu = float(preu_text)
                quantitat = extreure_quantitat(nom)
                productes.append({'producte': nom, 'marca': 'Carrefour', 'supermercat': 'Carrefour', 'preu': preu, 'quantitat': quantitat, 'envas': ''})
            except:
                continue
        return productes

    def scrape_categoria(self, nom_cat, codi_cat, max_productes=100):
        print(f"  📂 Categoria: {nom_cat}")
        count = 0
        offset = 0
        noms_anteriors = set()
        reintents = 0
        while count < max_productes:
            driver = None
            try:
                driver = self._crear_driver()
                url = f'{self.base_url}/{nom_cat}/{codi_cat}/c?offset={offset}'
                productes = self.scrape_pagina(driver, url)

                if not productes:
                    if reintents < 2:
                        reintents += 1
                        print(f"    offset={offset} -> 0 productes, reintentant ({reintents}/2)...")
                        time.sleep(15)
                        continue
                    else:
                        print(f"    offset={offset} -> 0 productes, parant")
                        break

                reintents = 0
                noms_actuals = set(p['producte'] for p in productes)
                if noms_actuals == noms_anteriors and offset > 0:
                    print(f"    ⚠️ Pagina repetida detectada, parant")
                    break
                noms_anteriors = noms_actuals
                self.productes.extend(productes)
                count += len(productes)
                print(f"    offset={offset} -> {len(productes)} productes")
                offset += 24
            except Exception as e:
                print(f"    ❌ Error offset={offset}: {e}")
                break
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            time.sleep(5)
        print(f"    ✅ {count} productes extrets")

    def scrape_all(self, max_per_categoria=100):
        print("\n🔴 Carrefour: extraient productes amb Selenium...")
        for nom_cat, codi_cat in self.categories:
            self.scrape_categoria(nom_cat, codi_cat, max_productes=max_per_categoria)
            time.sleep(10)
        print(f"✅ Carrefour: {len(self.productes)} productes extrets")
        return self.productes


class BonPreuEsclatScraper:
    def __init__(self, categories_filtre=None):
        self.base_url = 'https://www.compraonline.bonpreuesclat.cat'
        self.productes = []
        # Si no s'especifica filtre, usar totes les categories
        if categories_filtre:
            self.categories_valides = categories_filtre
        else:
            self.categories_valides = [
                'frescos', 'alimentaci', 'begudes', 'congelats',
                'ctics',        # troba 'lactics' i 'lactics i ous'
                'cura',         # troba 'cura personal'
                'neteja',       # troba 'neteja de la llar'
                'per la llar',
                'mascotes',     # troba 'espai mascotes'
                'nadons',
                'parafarm',     # troba 'parafarmacia'
            ]

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def descobrir_categories(self, driver):
        print("  🔍 Descobrint categories principals...")
        driver.get(self.base_url)
        driver.add_cookie({
            "name": "language",
            "value": "es-ES",
            "domain": "www.compraonline.bonpreuesclat.cat"
        })
        driver.refresh()
        time.sleep(8)
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
        categories = []
        uuids_vistos = set()
        for link in links:
            href = link.get_attribute('href')
            text = link.get_attribute('innerText').strip().lower()
            if not href or not text:
                continue
            uuid = href.split('/')[-1].split('?')[0]
            if uuid in uuids_vistos:
                continue
            if any(cat in text for cat in self.categories_valides):
                uuids_vistos.add(uuid)
                url_neta = f"{self.base_url}/categories/{href.split('/categories/')[1].split('?')[0]}"
                categories.append((text.title(), url_neta))
        print(f"  ✅ {len(categories)} categories principals trobades")
        return categories

    def get_subcategories(self, driver, url):
        """Retorna subcategories directes d'una URL basant-se en el nombre de segments del path"""
        path_pare = url.split('/categories/')[-1].split('?')[0]
        segments_pare = [s for s in path_pare.split('/') if s]
        slug_pare = segments_pare[0]  # primer segment = nom de la categoria
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
            # Subcategoria directa: comenca amb el slug pare i te exactament 1 segment mes
            if (len(segments) == n_segments_pare + 1
                    and segments[0] == slug_pare
                    and len(uuid) > 10
                    and uuid not in uuids_vistos):
                uuids_vistos.add(uuid)
                url_neta = f"{self.base_url}/categories/{path}"
                subcats.append((text, url_neta))
        return subcats

    def convertir_pes(self, pes_text):
        import re
        match = re.match(r'([0-9.]+)(kg|l|g|ml)', pes_text.strip(), re.IGNORECASE)
        if not match:
            return pes_text
        val = float(match.group(1))
        unitat = match.group(2).lower()
        if unitat == 'kg':
            if val < 1:
                return str(int(val*1000)) + ' g'
            v = int(val) if val == int(val) else val
            return str(v) + ' kg'
        elif unitat == 'l':
            if val < 1:
                return str(int(val*1000)) + ' ml'
            v = int(val) if val == int(val) else val
            return str(v) + ' l'
        return pes_text

    def extreure_productes_pagina(self, driver, url):
        """Extreu productes d'una URL amb scroll infinit"""
        count = 0
        try:
            driver.get(url)
            time.sleep(4)
            anterior = 0
            for i in range(5):
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(1)
                actual = len(driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]'))
                if actual == anterior and i > 1:
                    break
                anterior = actual
            noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
            preus = driver.find_elements(By.CSS_SELECTOR, 'span[data-test="fop-price"]')
            for i in range(min(len(noms), len(preus))):
                try:
                    nom = noms[i].get_attribute('innerText').strip()
                    preu_text = preus[i].get_attribute('innerText').strip()
                    preu_text = preu_text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                    preu = float(preu_text)
                    try:
                        contenidor = noms[i].find_element(By.XPATH, '../../../..')
                        pes_el = contenidor.find_element(By.CSS_SELECTOR, 'span[class*="weight"]')
                        quantitat = self.convertir_pes(pes_el.get_attribute('innerText').strip())
                    except:
                        quantitat = ''
                    if nom and preu > 0:
                        self.productes.append({
                            'producte': nom,
                            'marca': 'Bon Preu / Esclat',
                            'supermercat': 'Bon Preu / Esclat',
                            'preu': preu,
                            'quantitat': quantitat,
                            'envas': ''
                        })
                        count += 1
                except:
                    continue
        except Exception as e:
            print(f"      ❌ Error: {e}")
        return count

    def scrape_recursiu(self, url, nivell=0, driver=None):
        """Descobreix i rasca recursivament totes les subcategories reutilitzant el driver"""
        prefix = '  ' * (nivell + 2)
        driver_propi = driver is None
        try:
            if driver_propi:
                driver = self._crear_driver()

            driver.get(url)
            time.sleep(5)
            for i in range(2):
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)

            subcats = self.get_subcategories(driver, url)
            nom_cat = url.split('/')[-2]

            if subcats:
                print(f"{prefix}📂 {nom_cat}: {len(subcats)} subcategories")
                for nom_sub, url_sub in subcats:
                    self.scrape_recursiu(url_sub, nivell + 1, driver=driver)
            else:
                # Categoria final — extreure productes amb el mateix driver
                count = self.extreure_productes_pagina(driver, url)
                print(f"{prefix}└ {nom_cat}: {count} productes")

        except Exception as e:
            nom_cat = url.split('/')[-2]
            print(f"{prefix}❌ Error {nom_cat}: {e}")
        finally:
            if driver_propi and driver:
                try:
                    driver.quit()
                except:
                    pass

    def scrape_all(self):
        print(f"\n🟡 Bon Preu / Esclat: extraient productes amb Selenium...")
        # Descobrir categories principals
        driver_descobrir = None
        categories = []
        try:
            driver_descobrir = self._crear_driver()
            categories = self.descobrir_categories(driver_descobrir)
        except Exception as e:
            print(f"  ❌ Error descobrint categories: {e}")
        finally:
            if driver_descobrir:
                try:
                    driver_descobrir.quit()
                except:
                    pass

        # Rasquejar cada categoria recursivament
        for nom_cat, url_cat in categories:
            print(f"  📂 Categoria principal: {nom_cat}")
            self.scrape_recursiu(url_cat, nivell=0)
            time.sleep(2)

        print(f"✅ Bon Preu / Esclat: {len(self.productes)} productes extrets")
        return self.productes


# EXECUTAR SCRAPERS
if __name__ == '__main__':
    import sys
    part = '1'
    for arg in sys.argv[1:]:
        if arg.startswith('--part='):
            part = arg.split('=')[1]

    print(f"🔧 Executant PART {part}")

    def desduplicar(productes):
        vistos = set()
        unics = []
        for p in productes:
            clau = (p.get('producte', '').strip().lower(), p.get('supermercat', '').strip().lower())
            if clau not in vistos:
                vistos.add(clau)
                unics.append(p)
        return unics

    def guardar_a_sheet(ws, productes):
        ws.clear()
        ws.append_row(['id', 'producte', 'marca', 'supermercat', 'preu', 'quantitat', 'envas', 'data'])
        data = datetime.now().strftime('%Y-%m-%d %H:%M')
        rows = []
        for i, p in enumerate(productes, start=1):
            p['data'] = data
            rows.append([
                i,
                p.get('producte', ''),
                p.get('marca', ''),
                p.get('supermercat', ''),
                p.get('preu', 0),
                p.get('quantitat', ''),
                p.get('envas', ''),
                p.get('data', '')
            ])
        ws.append_rows(rows)

    if part == '1':
        print("\n" + "="*60)
        print("PART 1: Mercadona + Bon Area")
        print("="*60)

        tots = []
        scraper_mercadona = MercadonaScraper()
        tots.extend(scraper_mercadona.scrape_all())

        scraper_bonarea = BonAreaScraper()
        tots.extend(scraper_bonarea.scrape_all())

        unics = desduplicar(tots)
        duplicats = len(tots) - len(unics)
        print(f"\n✅ Part 1: {len(tots)} -> {len(unics)} unics ({duplicats} duplicats eliminats)")

        ws_temp1 = sheet.worksheet('Preus_Temp_1')
        guardar_a_sheet(ws_temp1, unics)
        print(f"✅ Preus_Temp_1 actualitzat amb {len(unics)} productes")

        ws_preus = sheet.worksheet('Preus')
        all_data = ws_temp1.get_all_values()
        ws_preus.clear()
        ws_preus.append_rows(all_data)
        print(f"✅ Preus actualitzat provisionalment amb {len(unics)} productes")

    elif part == '2':
        print("\n" + "="*60)
        print("PART 2: Dia")
        print("="*60)

        tots = []
        scraper_dia = DiaScraper()
        tots.extend(scraper_dia.scrape_all())

        unics_part2 = desduplicar(tots)
        print(f"\n✅ Part 2: {len(unics_part2)} productes unics de Dia")

        print("📖 Llegint productes de la Part 1...")
        try:
            ws_temp1 = sheet.worksheet('Preus_Temp_1')
            files_part1 = ws_temp1.get_all_records()
            productes_part1 = [{
                'producte': f['producte'],
                'marca': f['marca'],
                'supermercat': f['supermercat'],
                'preu': float(f['preu']),
                'quantitat': f['quantitat'],
                'envas': f.get('envas', ''),
                'data': f['data']
            } for f in files_part1]
            print(f"✅ {len(productes_part1)} productes de la Part 1 llegits")
        except Exception as e:
            print(f"❌ Error llegint Part 1: {e}")
            productes_part1 = []

        tots_combinats = productes_part1 + unics_part2
        unics_finals = desduplicar(tots_combinats)
        duplicats = len(tots_combinats) - len(unics_finals)
        print(f"✅ Total combinat: {len(tots_combinats)} -> {len(unics_finals)} unics ({duplicats} duplicats eliminats)")

        ws_temp2 = sheet.worksheet('Preus_Temp_2')
        guardar_a_sheet(ws_temp2, unics_finals)
        print(f"✅ Preus_Temp_2 actualitzat amb {len(unics_finals)} productes")

        ws_preus = sheet.worksheet('Preus')
        all_data = ws_temp2.get_all_values()
        ws_preus.clear()
        ws_preus.append_rows(all_data)
        print(f"✅ Preus actualitzat provisionalment amb {len(unics_finals)} productes")

    elif part == '3':
        print("\n" + "="*60)
        print("PART 3: Bon Preu/Esclat - Frescos + Alimentació + Begudes")
        print("="*60)

        tots = []
        scraper_bp = BonPreuEsclatScraper(categories_filtre=[
            'frescos', 'alimentaci', 'begudes'
        ])
        tots.extend(scraper_bp.scrape_all())

        unics_part3 = desduplicar(tots)
        print(f"\n✅ Part 3: {len(unics_part3)} productes unics")

        print("📖 Llegint productes de les Parts 1+2...")
        try:
            ws_temp2 = sheet.worksheet('Preus_Temp_2')
            files_part2 = ws_temp2.get_all_records()
            productes_parts12 = [{
                'producte': f['producte'],
                'marca': f['marca'],
                'supermercat': f['supermercat'],
                'preu': float(f['preu']),
                'quantitat': f['quantitat'],
                'envas': f.get('envas', ''),
                'data': f['data']
            } for f in files_part2]
            print(f"✅ {len(productes_parts12)} productes de Parts 1+2 llegits")
        except Exception as e:
            print(f"❌ Error llegint Parts 1+2: {e}")
            productes_parts12 = []

        tots_combinats = productes_parts12 + unics_part3
        unics_finals = desduplicar(tots_combinats)
        print(f"✅ Total: {len(unics_finals)} productes")

        ws_temp = sheet.worksheet('Preus_Temp')
        guardar_a_sheet(ws_temp, unics_finals)
        print(f"✅ Preus_Temp actualitzat amb {len(unics_finals)} productes")

        ws_preus = sheet.worksheet('Preus')
        all_data = ws_temp.get_all_values()
        ws_preus.clear()
        ws_preus.append_rows(all_data)
        print(f"✅ Preus actualitzat provisionalment amb {len(unics_finals)} productes")

    elif part == '4':
        print("\n" + "="*60)
        print("PART 4: Bon Preu/Esclat - Congelats + Làctics + Cura + Neteja + Per la llar + Mascotes + Nadons + Parafarmàcia")
        print("="*60)

        tots = []
        scraper_bp = BonPreuEsclatScraper(categories_filtre=[
            'congelats', 'ctics', 'cura', 'neteja',
            'per la llar', 'mascotes', 'nadons', 'parafarm'
        ])
        tots.extend(scraper_bp.scrape_all())

        unics_part4 = desduplicar(tots)
        print(f"\n✅ Part 4: {len(unics_part4)} productes unics")

        print("📖 Llegint productes de les Parts 1+2+3...")
        try:
            ws_temp = sheet.worksheet('Preus_Temp')
            files_prev = ws_temp.get_all_records()
            productes_prev = [{
                'producte': f['producte'],
                'marca': f['marca'],
                'supermercat': f['supermercat'],
                'preu': float(f['preu']),
                'quantitat': f['quantitat'],
                'envas': f.get('envas', ''),
                'data': f['data']
            } for f in files_prev]
            print(f"✅ {len(productes_prev)} productes llegits")
        except Exception as e:
            print(f"❌ Error llegint parts anteriors: {e}")
            productes_prev = []

        tots_combinats = productes_prev + unics_part4
        unics_finals = desduplicar(tots_combinats)
        print(f"✅ Total: {len(unics_finals)} productes")

        ws_temp = sheet.worksheet('Preus_Temp')
        guardar_a_sheet(ws_temp, unics_finals)
        print(f"✅ Preus_Temp actualitzat amb {len(unics_finals)} productes")

        ws_preus = sheet.worksheet('Preus')
        all_data = ws_temp.get_all_values()
        ws_preus.clear()
        ws_preus.append_rows(all_data)
        print(f"✅ Preus actualitzat provisionalment amb {len(unics_finals)} productes")

    elif part == '5':
        print("\n" + "="*60)
        print("PART 5: Carrefour (sense limit)")
        print("="*60)

        tots = []
        scraper_carrefour = CarrefourScraper()
        tots.extend(scraper_carrefour.scrape_all(max_per_categoria=9999))

        unics_part5 = desduplicar(tots)
        print(f"\n✅ Part 5: {len(unics_part5)} productes unics de Carrefour")

        print("📖 Llegint productes de les Parts 1+2+3+4...")
        try:
            ws_temp = sheet.worksheet('Preus_Temp')
            files_prev = ws_temp.get_all_records()
            productes_prev = [{
                'producte': f['producte'],
                'marca': f['marca'],
                'supermercat': f['supermercat'],
                'preu': float(f['preu']),
                'quantitat': f['quantitat'],
                'envas': f.get('envas', ''),
                'data': f['data']
            } for f in files_prev]
            print(f"✅ {len(productes_prev)} productes llegits")
        except Exception as e:
            print(f"❌ Error llegint parts anteriors: {e}")
            productes_prev = []

        tots_combinats = productes_prev + unics_part5
        unics_finals = desduplicar(tots_combinats)
        duplicats = len(tots_combinats) - len(unics_finals)
        print(f"✅ Total final: {len(tots_combinats)} -> {len(unics_finals)} unics ({duplicats} duplicats eliminats)")

        ws_temp_final = sheet.worksheet('Preus_Temp')
        guardar_a_sheet(ws_temp_final, unics_finals)

        ws_preus = sheet.worksheet('Preus')
        all_data = ws_temp_final.get_all_values()
        ws_preus.clear()
        ws_preus.append_rows(all_data)
        print(f"✅ Preus actualitzat amb {len(unics_finals)} productes TOTALS")

    print("\n" + "="*60)
    print(f"✅ PART {part} COMPLETADA!")
    print("="*60)

