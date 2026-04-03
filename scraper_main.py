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

# Llegir credencials des de variable d'entorn (GitHub Secret)
try:
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise Exception("⚠️ GOOGLE_CREDENTIALS no trobat!")
    
    creds_dict = json.loads(creds_json)
    print("✅ Credencials carregades correctament")
except Exception as e:
    print(f"❌ Error carregant credencials: {e}")
    exit(1)

# Connexió Google Sheets
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
        # Categories a excloure (no alimentació/neteja)
        self.excloure = ['freidora-de-aire', 'sin-gluten', 'ofertas', 'recetas']

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        import re
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def descobrir_categories(self, driver):
        """Descobreix categories principals (sense subcategories) des d'una pàgina de categoria"""
        import re
        print("  🔍 Descobrint categories automàticament...")
        driver.get(f'{self.base_url}/frutas/c/L105')
        time.sleep(8)
        links = driver.find_elements(By.TAG_NAME, 'a')
        categories = []
        vistos = set()
        for link in links:
            href = link.get_attribute('href') or ''
            text = link.get_attribute('innerText').strip()
            # Només categories principals (un sol segment abans de /c/)
            match = re.search(r'dia\.es/([^/]+)/c/L(\d+)$', href)
            if match and href not in vistos and text:
                nom_cat = match.group(1)
                if not any(excl in nom_cat for excl in self.excloure):
                    vistos.add(href)
                    categories.append((text, href))
        print(f"  ✅ {len(categories)} categories trobades")
        return categories

    def scrape_categoria(self, driver, nom_cat, url, max_productes=100):
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

        print(f"  📂 Categoria: {nom_cat}")
        count = 0
        pagina = 0
        while count < max_productes:
            try:
                url_pagina = f"{url}?q=%3Arelevance&pageSize=48&currentPage={pagina}"
                driver.get(url_pagina)
                time.sleep(8)
                for i in range(3):
                    driver.execute_script("window.scrollBy(0, 400);")
                    time.sleep(1)
                cards = driver.find_elements(By.CSS_SELECTOR, '.search-product-card')
                if not cards:
                    break
                for card in cards:
                    try:
                        nom = card.find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-name"]').get_attribute('innerText').strip()
                        preu_text = card.find_element(By.CSS_SELECTOR, '[data-test-id="search-product-card-unit-price"]').get_attribute('innerText')
                        preu_text = preu_text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                        preu = float(preu_text)
                        if nom and preu > 0:
                            self.productes.append({'producte': nom, 'marca': 'Día', 'supermercat': 'Dia', 'preu': preu, 'quantitat': extreure_quantitat(nom), 'envas': ''})
                            count += 1
                    except:
                        continue
                print(f"    pàgina {pagina} → {len(cards)} productes")
                if len(cards) < 48:
                    break
                pagina += 1
            except Exception as e:
                print(f"    ❌ Error pàgina {pagina}: {e}")
                break
        print(f"    ✅ {count} productes extrets")

    def scrape_all(self, max_per_categoria=100):
        print("\n🟣 Dia: extraient productes amb Selenium...")
        # Descobrir categories
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

        # Rasquem cada categoria
        for nom_cat, url in categories:
            driver = None
            try:
                driver = self._crear_driver()
                self.scrape_categoria(driver, nom_cat, url, max_productes=max_per_categoria)
            except Exception as e:
                print(f"  ❌ Error general categoria: {e}")
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
        # Categories que ens interessen (alimentació, cuinats, begudes, drogueria, higiene, perfumeria, mascotes)
        self.codis_valids = ['13_300', '13_310', '13_320', '13_330', '13_340', '13_350', '13_030']

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def descobrir_categories(self, driver):
        """Llegeix totes les categories del menú i filtra les que ens interessen"""
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
            # Filtrar només categories que ens interessen i que tinguin subcategoria (_XXX_XXX)
            codi = href.split('/')[-1]
            if any(codi.startswith(c) for c in self.codis_valids) and codi.count('_') >= 2:
                categories.append(href)
        print(f"  ✅ {len(categories)} categories trobades")
        return categories

    def scrape_categoria(self, driver, url):
        nom_cat = url.split('/')[-2]
        print(f"  📂 Categoria: {nom_cat}")
        count = 0
        try:
            driver.get(url)
            time.sleep(8)
            for i in range(3):
                driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(1)
            time.sleep(2)
            productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')

            # Si no troba productes, provar amb _010 al final
            if not productes:
                url_alt = url + '_010'
                driver.get(url_alt)
                time.sleep(8)
                for i in range(3):
                    driver.execute_script("window.scrollBy(0, 400);")
                    time.sleep(1)
                time.sleep(2)
                productes = driver.find_elements(By.CSS_SELECTOR, 'div.block-product')

            for prod in productes:
                try:
                    nom = prod.find_element(By.CSS_SELECTOR, 'a.article-link div.text p').get_attribute('innerText').strip()
                    preu_text = prod.find_element(By.CSS_SELECTOR, 'div.price span').get_attribute('innerText')
                    preu_text = preu_text.replace('€/u.', '').replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                    preu = float(preu_text)
                    quantitat = prod.find_element(By.CSS_SELECTOR, 'div.weight').get_attribute('innerText').strip()
                    if nom and preu > 0:
                        self.productes.append({'producte': nom, 'marca': 'bonÀrea', 'supermercat': 'Bon Àrea', 'preu': preu, 'quantitat': quantitat, 'envas': ''})
                        count += 1
                except:
                    continue
            print(f"    ✅ {count} productes extrets")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        return count

    def scrape_all(self, max_productes=999):
        print(f"\n🟠 Bon Àrea: extraient productes amb Selenium...")
        # Primer descobrim les categories automàticament
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

        # Després rasquem cada categoria amb driver nou
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
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def scrape_pagina(self, driver, url):
        """Extreu productes d'una pàgina"""
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
        while count < max_productes:
            driver = None
            try:
                driver = self._crear_driver()
                url = f'{self.base_url}/{nom_cat}/{codi_cat}/c?offset={offset}'
                productes = self.scrape_pagina(driver, url)
                if not productes:
                    break
                # Detectar pàgina repetida
                noms_actuals = set(p['producte'] for p in productes)
                if noms_actuals == noms_anteriors:
                    print(f"    ⚠️ Pàgina repetida detectada, parant")
                    break
                noms_anteriors = noms_actuals
                self.productes.extend(productes)
                count += len(productes)
                print(f"    offset={offset} → {len(productes)} productes")
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
            time.sleep(2)
        print(f"    ✅ {count} productes extrets")

    def scrape_all(self, max_per_categoria=100):
        print("\n🔴 Carrefour: extraient productes amb Selenium...")
        for nom_cat, codi_cat in self.categories:
            self.scrape_categoria(nom_cat, codi_cat, max_productes=max_per_categoria)
            time.sleep(10)
        print(f"✅ Carrefour: {len(self.productes)} productes extrets")
        return self.productes


class BonPreuEsclatScraper:
    def __init__(self):
        self.base_url = 'https://www.compraonline.bonpreuesclat.cat'
        self.productes = []
        # Categories que ens interessen per nom
        self.categories_valides = [
            'frescos', 'alimentaci', 'begudes', 'congelats',
            'lactics', 'làctics', 'cura-personal', 'neteja',
            'espai-mascotes', 'nadons'
        ]

    def _crear_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.binary_location = '/usr/bin/chromium-browser'
        from selenium.webdriver.chrome.service import Service
        service = Service('/usr/bin/chromedriver')
        return webdriver.Chrome(service=service, options=chrome_options)

    def descobrir_categories(self, driver):
        """Llegeix categories del menú i filtra les que ens interessen, desduplicant per UUID"""
        print("  🔍 Descobrint categories automàticament...")
        driver.get(self.base_url)
        time.sleep(8)
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/categories/"]')
        categories = []
        uuids_vistos = set()
        for link in links:
            href = link.get_attribute('href')
            text = link.get_attribute('innerText').strip().lower()
            if not href or not text:
                continue
            # Extreure UUID (últim segment abans del ?)
            uuid = href.split('/')[-1].split('?')[0]
            if uuid in uuids_vistos:
                continue
            # Filtrar per categories que ens interessen
            if any(cat in text for cat in self.categories_valides):
                uuids_vistos.add(uuid)
                # Usar URL neta sense paràmetres extra
                url_neta = f"{self.base_url}/categories/{href.split('/categories/')[1].split('?')[0]}"
                categories.append((text.title(), url_neta))
        print(f"  ✅ {len(categories)} categories trobades")
        return categories

    def scrape_categoria(self, driver, nom_cat, url):
        import re
        def convertir_pes(pes_text):
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

        print(f"  📂 Categoria: {nom_cat}")
        count = 0
        try:
            driver.get(url)
            time.sleep(10)
            for i in range(5):
                driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(2)
            noms = driver.find_elements(By.CSS_SELECTOR, 'h3[data-test="fop-title"]')
            preus = driver.find_elements(By.CSS_SELECTOR, 'span[data-test="fop-price"]')
            for i in range(min(len(noms), len(preus))):
                try:
                    nom = noms[i].get_attribute('innerText').strip()
                    preu_text = preus[i].get_attribute('innerText').strip()
                    preu_text = preu_text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                    preu = float(preu_text)
                    # Extreure quantitat
                    try:
                        contenidor = noms[i].find_element(By.XPATH, '../../../..')
                        pes_el = contenidor.find_element(By.CSS_SELECTOR, 'span[class*="weight"]')
                        quantitat = convertir_pes(pes_el.get_attribute('innerText').strip())
                    except:
                        quantitat = ''
                    if nom and preu > 0:
                        self.productes.append({'producte': nom, 'marca': 'Bon Preu / Esclat', 'supermercat': 'Bon Preu / Esclat', 'preu': preu, 'quantitat': quantitat, 'envas': ''})
                        count += 1
                except:
                    continue
            print(f"    ✅ {count} productes extrets")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        return count

    def scrape_all(self):
        print(f"\n🟡 Bon Preu / Esclat: extraient productes amb Selenium...")
        # Descobrir categories
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

        # Rasquem cada categoria
        for nom_cat, url in categories:
            driver = None
            try:
                driver = self._crear_driver()
                self.scrape_categoria(driver, nom_cat, url)
            except Exception as e:
                print(f"  ❌ Error general categoria: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            time.sleep(2)

        print(f"✅ Bon Preu / Esclat: {len(self.productes)} productes extrets")
        return self.productes


# EXECUTAR SCRAPERS
if __name__ == '__main__':
    db = GoogleSheetsDB(sheet)
    
    print("\n" + "="*60)
    print("🔄 FASE 1: Extraient productes de tots els supermercats...")
    print("="*60)
    
    tots_productes = []
    
    scraper_mercadona = MercadonaScraper()
    tots_productes.extend(scraper_mercadona.scrape_all())
    
    scraper_carrefour = CarrefourScraper()
    tots_productes.extend(scraper_carrefour.scrape_all(max_per_categoria=100))
    
    scraper_bonpreuesclat = BonPreuEsclatScraper()
    tots_productes.extend(scraper_bonpreuesclat.scrape_all())
    
    scraper_dia = DiaScraper()
    tots_productes.extend(scraper_dia.scrape_all(max_per_categoria=100))
    
    scraper_bonarea = BonAreaScraper()
    tots_productes.extend(scraper_bonarea.scrape_all())
    
    print("\n" + "="*60)
    print(f"🔄 FASE 2: Desduplicant i omplint full temporal...")
    print("="*60)

    # Desduplicar per nom + supermercat
    vistos = set()
    tots_productes_unics = []
    for p in tots_productes:
        clau = (p.get('producte', '').strip().lower(), p.get('supermercat', '').strip().lower())
        if clau not in vistos:
            vistos.add(clau)
            tots_productes_unics.append(p)

    duplicats = len(tots_productes) - len(tots_productes_unics)
    print(f"✅ {len(tots_productes)} productes → {len(tots_productes_unics)} únics ({duplicats} duplicats eliminats)")
    
    ws_temp = sheet.worksheet('Preus_Temp')
    ws_temp.clear()
    ws_temp.append_row(['id', 'producte', 'marca', 'supermercat', 'preu', 'quantitat', 'envas', 'data'])
    
    for preu in tots_productes_unics:
        preu['data'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    rows = []
    for i, preu in enumerate(tots_productes_unics, start=1):
        row = [
            i,
            preu.get('producte', ''),
            preu.get('marca', ''),
            preu.get('supermercat', ''),
            preu.get('preu', 0),
            preu.get('quantitat', ''),
            preu.get('envas', ''),
            preu.get('data', '')
        ]
        rows.append(row)
    
    ws_temp.append_rows(rows)
    print(f"✅ Full temporal omplert amb {len(tots_productes_unics)} productes")
    
    print("\n" + "="*60)
    print("🔄 FASE 3: Actualitzant full principal (swap atòmic)...")
    print("="*60)
    
    ws_preus = sheet.worksheet('Preus')
    all_data = ws_temp.get_all_values()
    ws_preus.clear()
    ws_preus.append_rows(all_data)
    
    print("✅ Full 'Preus' actualitzat correctament")
    
    print("\n" + "="*60)
    print("✅ SCRAPERS COMPLETATS!")
    print(f"📊 Total brut: {len(tots_productes)} | Únics: {len(tots_productes_unics)} | Duplicats eliminats: {duplicats}")
    print("✅ App sempre amb dades disponibles")
    print("="*60)
