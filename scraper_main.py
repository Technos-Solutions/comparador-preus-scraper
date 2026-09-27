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

# Nomes per a BonPreuEsclatScraper: Chrome real (headed) + Xvfb via
# SeleniumBase per evitar la pantalla "Human Verification" que Bon Preu
# mostra a Selenium en mode headless (verificat amb diagnostic aillat).
from seleniumbase import Driver as SeleniumBaseDriver

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
    # Setembre 2026 — validat amb diagnostics reals (debug_carrefour_categoria.py):
    # - El Selenium headless queda aturat a "Just a moment..." de Cloudflare;
    #   cal Chrome real (headed) + Xvfb via SeleniumBase. El repte de
    #   Cloudflare apareix de forma intermitent (algunes pagines si, d'altres
    #   no) i es resol clicant la casella (uc_gui_click_cf).
    # - El selector antic article[data-test="search-grid-result"] ja no
    #   existeix: cada producte es un <div data-origin="list" app_price="...">
    #   amb el nom a l'atribut alt de la imatge.
    # - Nomes es llegeix la graella principal (ul.product-card-list__list, 24
    #   productes per pagina amb ?offset=N): fora de la graella hi ha blocs de
    #   destacats/carrusels que es repeteixen a totes les pagines.
    # - La graella es renderitza a mesura que es fa scroll: cal baixar pas a
    #   pas, saltar al final deixava pagines amb nomes 13 de 24 productes.
    # - Cloudflare bloqueja ("Sorry, you have been blocked") qualsevol pagina
    #   a partir d'offset=1008: les categories de mes de ~1000 productes es
    #   recorren baixant a les subcategories (debug_carrefour_arbre.py: 103
    #   fulles, totes <= 1008, ~16.800 productes en total). Algunes
    #   categories (Mascotas, Parafarmacia, Vinos) son portades sense graella
    #   i tambe cal baixar-hi.
    PAS_OFFSET = 24
    LIMIT_PAGINACIO = 1008
    PROFUNDITAT_MAXIMA = 3
    # Si les subcategories sumen menys d'aquest % del total de la mare (hi
    # ha productes que no pengen de cap subcategoria, o una subcategoria no
    # ha carregat), es recorre tambe la mare fins al limit de paginacio.
    COBERTURA_MINIMA = 0.97
    # El job de GitHub Actions te un limit de 6h i les dades nomes s'escriuen
    # a Sheets al final: s'atura el scraping amb marge per poder-les desar.
    TEMPS_MAXIM_SEGONS = 5 * 3600

    def __init__(self):
        self.web = 'https://www.carrefour.es'
        self.base_url = f'{self.web}/supermercado'
        self.productes = []
        self.vistos = set()
        self.driver = None
        self.reinicis = 0
        self.inici = None
        self.incidencies = []
        self.categories = [
            ('frescos', 'cat20002'),
            ('la-despensa', 'cat20001'),
            ('bebidas', 'cat20003'),
            ('drogueria-y-limpieza', 'cat20005'),
            ('cuidado-personal-e-higiene', 'cat20004'),
            ('congelados', 'cat21449123'),
            ('bebe', 'cat20006'),
            ('mascotas', 'cat20007'),
            ('parafarmacia', 'cat20008'),
        ]

    def _temps_esgotat(self):
        return self.inici is not None and time.time() - self.inici > self.TEMPS_MAXIM_SEGONS

    def _superar_cloudflare(self, url, max_intents=3):
        for intent in range(1, max_intents + 1):
            # A les proves el repte no s'ha resolt mai sol esperant, sempre
            # ha calgut clicar la casella: s'espera poc abans de clicar.
            for _ in range(3):
                if 'just a moment' not in self.driver.get_title().lower():
                    return True
                time.sleep(2)
            try:
                self.driver.uc_gui_click_cf()
                time.sleep(4)
            except Exception:
                pass
            if 'just a moment' not in self.driver.get_title().lower():
                return True
            print(f"    ⏳ Cloudflare persisteix (intent {intent}), reconnectant...")
            self.driver.uc_open_with_reconnect(url, reconnect_time=8)
            time.sleep(3)
        return False

    def _crear_driver_nou(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.reinicis += 1
        url = f'{self.base_url}/frescos/cat20002/c'
        self.driver = SeleniumBaseDriver(uc=True, headed=True)
        self.driver.uc_open_with_reconnect(url, reconnect_time=6)
        time.sleep(3)
        self._superar_cloudflare(url)
        try:
            self.driver.click('#onetrust-accept-btn-handler', timeout=8)
            time.sleep(2)
        except Exception:
            pass

    def _carregar_tota_la_pagina(self):
        estable = 0
        anterior = -1
        for _ in range(40):
            self.driver.execute_script('window.scrollBy(0, 600);')
            time.sleep(0.8)
            actual = len(self.driver.find_elements('ul.product-card-list__list div[data-origin="list"]'))
            al_final = self.driver.execute_script(
                'return window.innerHeight + window.scrollY >= document.body.scrollHeight - 50;')
            if actual == anterior and al_final:
                estable += 1
                if estable >= 2:
                    break
            else:
                estable = 0
            anterior = actual
        return max(anterior, 0)

    @staticmethod
    def _parse_preu(text):
        net = text.replace('€', '').replace('\xa0', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(net)

    def _total_categoria(self):
        # Nomes com a cota superior per saber quan s'acaba la paginacio; si
        # no es troba, s'atura igualment quan una pagina surt buida.
        import re
        trobats = re.findall(r'(\d[\d\.]*)\s+(?:productos|resultados)', self.driver.get_page_source())
        valors = [int(t.replace('.', '')) for t in trobats if t.replace('.', '').isdigit()]
        return max(valors) if valors else None

    def _subcategories(self, cami_node):
        """Links de categoria un nivell per sota del node actual
        (cami_node + '/<segment>/catNNN/c'), en ordre d'aparicio."""
        links = self.driver.execute_script("""
            const out = [];
            document.querySelectorAll('a[href]').forEach(a => {
                let h = (a.getAttribute('href') || '').split('?')[0].split('#')[0];
                h = h.replace(/^https?:\\/\\/www\\.carrefour\\.es/, '');
                const m = h.match(/^(\\/supermercado\\/.+)\\/(cat\\d+)\\/c$/);
                if (m) out.push([m[1], m[2], (a.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 50)]);
            });
            return out;
        """)
        fills = {}
        for cami, codi, text in links:
            if cami.startswith(cami_node + '/') and cami.count('/') == cami_node.count('/') + 1:
                fills.setdefault(codi, (cami, text or cami.split('/')[-1]))
        return fills

    def scrape_pagina(self, url, esperats=None):
        """Retorna la llista de productes de la graella, o None si Cloudflare
        no ha deixat passar. Si se sap quants productes hi hauria d'haver i
        n'han carregat menys, torna a fer scroll des de dalt un cop."""
        import re
        def extreure_quantitat(nom):
            # Detecta "pack de N <paraula> de X <unitat>" (unidades, bolsitas,
            # brik, botellas...) i retorna la quantitat TOTAL (N x X), no la
            # d'una sola unitat. Sense això, el preu del pack sencer es
            # dividia només per la mida d'un got/bossa, inflant molt el
            # preu/100g o preu/l dels productes en pack (detectat amb
            # l'auditoria de preus sospitosos de Comparacions_v2: iogurts en
            # pack de Danone/Nestlé sortien 4-8 vegades més cars del compte).
            pack = re.search(
                r'pack\s+de\s+(\d+)\s+\w+\s+de\s+(\d+[.,]?\d*)\s*(kg|g|l|ml|cl)',
                nom, re.IGNORECASE
            )
            if pack:
                n = int(pack.group(1))
                val = float(pack.group(2).replace(',', '.'))
                unitat = pack.group(3).lower()
                total = n * val
                total_str = str(int(total)) if total == int(total) else str(total)
                return f"{total_str} {unitat}"

            matches = re.findall(r'(\d+[.,]?\d*)\s*(kg|g|l|ml|cl|ud|unidades?)', nom, re.IGNORECASE)
            if matches:
                val, unitat = matches[-1]
                return f"{val} {unitat.lower()}"
            return ''

        self.driver.get(url)
        time.sleep(3)
        if not self._superar_cloudflare(url):
            return None
        carregats = self._carregar_tota_la_pagina()
        if esperats and 0 < carregats < esperats:
            time.sleep(2)
            self.driver.execute_script('window.scrollTo(0, 0);')
            carregats = self._carregar_tota_la_pagina()
            if carregats < esperats:
                print(f"    ⚠️ Carrega parcial: {carregats} de {esperats} productes esperats")

        targetes = self.driver.execute_script("""
            const out = [];
            document.querySelectorAll('ul.product-card-list__list div[data-origin="list"]').forEach(c => {
                const img = c.querySelector('img.product-card__image');
                const a = c.querySelector('a.product-card__media-link');
                out.push({
                    nom: img ? (img.getAttribute('alt') || '').trim() : '',
                    preu: c.getAttribute('app_price') || '',
                    link: a ? (a.getAttribute('href') || '') : ''
                });
            });
            return out;
        """)
        productes = []
        for t in targetes:
            try:
                if not t['nom'] or not t['preu']:
                    continue
                preu = self._parse_preu(t['preu'])
                productes.append((t['link'] or t['nom'], {
                    'producte': t['nom'], 'marca': 'Carrefour', 'supermercat': 'Carrefour',
                    'preu': preu, 'quantitat': extreure_quantitat(t['nom']), 'envas': ''
                }))
            except Exception:
                continue
        return productes

    def _afegir(self, productes):
        # Deduplicacio global per link: un mateix producte pot sortir a
        # diverses categories (p. ex. Bebe i Parafarmacia > Bebe).
        nous = 0
        for link, p in productes:
            if link not in self.vistos:
                self.vistos.add(link)
                self.productes.append(p)
                nous += 1
        return nous

    def _paginar(self, url_base, total, sagnat, offset_inicial=PAS_OFFSET):
        """Recorre les pagines d'un llistat a partir d'offset_inicial, sense
        passar mai del limit de paginacio de Cloudflare."""
        limit = min(total, self.LIMIT_PAGINACIO) if total else self.LIMIT_PAGINACIO
        offset = offset_inicial
        nous_totals = 0
        while offset < limit:
            if self._temps_esgotat():
                print(f"{sagnat}⏱️ Temps maxim esgotat, parant per poder desar les dades")
                break
            url = f'{url_base}?offset={offset}'
            esperats = min(self.PAS_OFFSET, limit - offset) if total else None
            try:
                productes = self.scrape_pagina(url, esperats)
                if not productes:
                    # Una pagina buida abans del total indicat no es normal:
                    # bloqueig o sessio degradada. Es reinicia el navegador i
                    # es reintenta un cop abans de donar el llistat per acabat.
                    if not total:
                        break
                    motiu = 'Cloudflare' if productes is None else '0 productes'
                    print(f"{sagnat}offset={offset} -> {motiu}, reiniciant navegador i reintentant...")
                    self._crear_driver_nou()
                    productes = self.scrape_pagina(url, esperats)
                    if not productes:
                        print(f"{sagnat}offset={offset} -> segueix sense productes, fi del llistat")
                        self.incidencies.append(f"{url}: pagina buida")
                        break
            except Exception as e:
                print(f"{sagnat}❌ Error offset={offset}: {e}")
                self.incidencies.append(f"{url}: {e}")
                break
            nous_totals += self._afegir(productes)
            offset += self.PAS_OFFSET
        return nous_totals

    def _obrir_node(self, url_base, cami):
        """Primera pagina d'una categoria: productes, total indicat i
        subcategories. El total nomes es coneix un cop oberta la pagina, aixi
        que si la graella ha carregat parcialment es torna a llegir."""
        productes = self.scrape_pagina(url_base)
        if productes is None:
            return None, None, {}
        total = self._total_categoria()
        fills = self._subcategories(cami)
        esperats = min(self.PAS_OFFSET, total) if total else None
        if esperats and 0 < len(productes) < esperats:
            productes = self.scrape_pagina(url_base, esperats) or productes
        return productes, total, fills

    def scrape_node(self, cami, codi, nom, nivell=0):
        """Recorre una categoria: si es pot paginar sencera (<= 1008
        productes) la pagina; si no, baixa a les subcategories. Retorna el
        nombre de productes que indica la categoria (per quadrar la suma)."""
        sagnat = '  ' * (nivell + 1)
        if self._temps_esgotat():
            print(f"{sagnat}⏱️ Temps maxim esgotat, no es fa {nom}")
            return 0
        url_base = f'{self.web}{cami}/{codi}/c'
        productes, total, fills = self._obrir_node(url_base, cami)
        if not productes and total is None and not fills:
            # Ni graella, ni total, ni subcategories: pagina que no ha
            # carregat be (a l'arbre de prova li va passar a una categoria).
            print(f"{sagnat}{nom}: pagina buida, reiniciant navegador i reintentant...")
            self._crear_driver_nou()
            productes, total, fills = self._obrir_node(url_base, cami)
            if not productes and total is None and not fills:
                print(f"{sagnat}⚠️ {nom}: segueix buida, es salta")
                self.incidencies.append(f"{url_base}: categoria buida")
                return 0

        cal_baixar = total is None or total > self.LIMIT_PAGINACIO
        if cal_baixar and fills and nivell < self.PROFUNDITAT_MAXIMA:
            print(f"{sagnat}📂 {nom} [{codi}]: {total} productes -> {len(fills)} subcategories")
            self._afegir(productes or [])
            suma = 0
            for sub_codi, (sub_cami, sub_nom) in fills.items():
                suma += self.scrape_node(sub_cami, sub_codi, sub_nom, nivell + 1)
            if total and suma < total * self.COBERTURA_MINIMA and not self._temps_esgotat():
                print(f"{sagnat}↳ {nom}: les subcategories sumen {suma} de {total}, "
                      f"es recorre tambe la categoria fins a {self.LIMIT_PAGINACIO}")
                nous = self._paginar(url_base, total, sagnat + '  ')
                print(f"{sagnat}↳ {nom}: {nous} productes nous del complement")
            return total or suma

        if total and total > self.LIMIT_PAGINACIO:
            print(f"{sagnat}⚠️ {nom}: {total} productes i sense subcategories, "
                  f"nomes es poden recorrer els primers {self.LIMIT_PAGINACIO}")
            self.incidencies.append(f"{url_base}: {total} productes sense subcategories")
        abans = len(self.productes)
        self._afegir(productes or [])
        self._paginar(url_base, total, sagnat + '  ')
        print(f"{sagnat}✅ {nom} [{codi}]: {len(self.productes) - abans} productes nous (indica {total})")
        return total or 0

    def scrape_all(self):
        print("\n🔴 Carrefour: extraient productes amb Chrome real (Xvfb), per subcategories...")
        self.inici = time.time()
        suma = 0
        try:
            self._crear_driver_nou()
            for slug, codi in self.categories:
                if self._temps_esgotat():
                    print(f"  ⏱️ Temps maxim esgotat, no es fa la categoria {slug}")
                    continue
                abans = len(self.productes)
                try:
                    suma += self.scrape_node(f'/supermercado/{slug}', codi, slug)
                except Exception as e:
                    # Un error en una categoria no ha de fer perdre les altres.
                    print(f"  ❌ Error a {slug}: {e}")
                    self.incidencies.append(f"{slug}: {e}")
                    self._crear_driver_nou()
                print(f"  📊 {slug}: {len(self.productes) - abans} productes nous "
                      f"(acumulat {len(self.productes)})")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
        minuts = (time.time() - self.inici) / 60
        print(f"✅ Carrefour: {len(self.productes)} productes unics extrets en {minuts:.0f} min "
              f"(els llistats n'indiquen {suma}; reinicis de navegador: {self.reinicis})")
        if self.incidencies:
            print(f"⚠️ Incidencies ({len(self.incidencies)}):")
            for inc in self.incidencies:
                print(f"   - {inc}")
        return self.productes


class BonPreuEsclatScraper:
    # Bon Preu detecta Selenium en mode headless i mostra una pantalla
    # "Human Verification" en lloc dels productes (verificat amb
    # diagnostic aillat: HTML de nomes ~10KB, sense cap producte). Amb
    # Chrome real (headed) + Xvfb via SeleniumBase (UC Mode) el bloqueig
    # desapareix. A mes, despres d'uns minuts d'activitat continuada la
    # sessio es degrada i comenca a retornar 0 productes a subcategories
    # que no poden estar buides (no es deteccio de bot, es una altra
    # cosa - possible limit intern del lloc); reiniciar el navegador quan
    # es detecten 2 subcategories seguides a 0 recupera dades valides de
    # seguida (verificat amb un run complet real).
    ZEROS_SEGUITS_PER_REINICI = 2

    def __init__(self, categories_filtre=None):
        self.base_url = 'https://www.compraonline.bonpreuesclat.cat'
        self.productes = []
        self.driver = None
        self.zeros_seguits = 0
        self.reinicis = 0
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

    def _crear_driver_nou(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.reinicis += 1
        self.driver = SeleniumBaseDriver(uc=True, headed=True)
        self.driver.uc_open_with_reconnect(self.base_url, reconnect_time=6)
        time.sleep(3)
        self.driver.add_cookie({
            "name": "language",
            "value": "ca",
            "domain": "www.compraonline.bonpreuesclat.cat"
        })
        self.driver.refresh()
        time.sleep(5)

    def descobrir_categories(self):
        print("  🔍 Descobrint categories principals...")
        driver = self.driver
        links = driver.find_elements('a[href*="/categories/"]')
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

    def get_subcategories(self, url):
        """Retorna subcategories directes d'una URL basant-se en el nombre de segments del path"""
        driver = self.driver
        path_pare = url.split('/categories/')[-1].split('?')[0]
        segments_pare = [s for s in path_pare.split('/') if s]
        slug_pare = segments_pare[0]  # primer segment = nom de la categoria
        n_segments_pare = len(segments_pare)

        links = driver.find_elements('a[href*="/categories/"]')
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

    def get_subcategories_amb_reintent(self, url, prefix):
        subcats = self.get_subcategories(url)
        if not subcats and self.zeros_seguits + 1 >= self.ZEROS_SEGUITS_PER_REINICI:
            print(f"{prefix}⚠️  0 subcategories i ja portava zeros seguits, reiniciant per comprovar...")
            self._crear_driver_nou()
            self.zeros_seguits = 0
            self.driver.get(url)
            time.sleep(3)
            subcats = self.get_subcategories(url)
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

    def extreure_productes_pagina(self, url):
        """Extreu productes d'una URL amb scroll infinit"""
        driver = self.driver
        count = 0
        try:
            driver.get(url)
            time.sleep(4)
            anterior = 0
            for i in range(8):
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(1.5)
                actual = len(driver.find_elements('h3[data-test="fop-title"]'))
                if actual == anterior and i > 1:
                    break
                anterior = actual
            noms = driver.find_elements('h3[data-test="fop-title"]')
            preus = driver.find_elements('span[data-test="fop-price"]')
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

    def scrape_recursiu(self, url, nivell=0):
        """Descobreix i rasca recursivament totes les subcategories reutilitzant el driver"""
        prefix = '  ' * (nivell + 2)
        try:
            self.driver.get(url)
            time.sleep(3)

            subcats = self.get_subcategories_amb_reintent(url, prefix)
            nom_cat = url.split('/')[-2]

            if subcats:
                print(f"{prefix}📂 {nom_cat}: {len(subcats)} subcategories")
                self.zeros_seguits = 0
                for nom_sub, url_sub in subcats:
                    self.scrape_recursiu(url_sub, nivell + 1)
            else:
                # Categoria final — extreure productes
                count = self.extreure_productes_pagina(url)
                if count == 0:
                    self.zeros_seguits += 1
                    if self.zeros_seguits >= self.ZEROS_SEGUITS_PER_REINICI:
                        print(f"{prefix}⚠️  {self.zeros_seguits} subcategories seguides a 0, reiniciant navegador i reintentant...")
                        self._crear_driver_nou()
                        self.zeros_seguits = 0
                        count = self.extreure_productes_pagina(url)
                if count > 0:
                    self.zeros_seguits = 0
                print(f"{prefix}└ {nom_cat}: {count} productes")

        except Exception as e:
            nom_cat = url.split('/')[-2]
            print(f"{prefix}❌ Error {nom_cat}: {e}")

    def scrape_all(self):
        print(f"\n🟡 Bon Preu / Esclat: extraient productes amb Chrome real (Xvfb)...")
        try:
            self._crear_driver_nou()
            categories = self.descobrir_categories()

            # Rasquejar cada categoria recursivament reutilitzant el mateix
            # driver (amb reinicis automatics si cal, gestionats a
            # scrape_recursiu).
            for nom_cat, url_cat in categories:
                print(f"  📂 Categoria principal: {nom_cat}")
                self.zeros_seguits = 0
                self.scrape_recursiu(url_cat, nivell=0)
                time.sleep(2)
        except Exception as e:
            print(f"  ❌ Error: {e}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

        print(f"✅ Bon Preu / Esclat: {len(self.productes)} productes extrets (reinicis de navegador: {self.reinicis})")
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
        tots.extend(scraper_carrefour.scrape_all())

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

