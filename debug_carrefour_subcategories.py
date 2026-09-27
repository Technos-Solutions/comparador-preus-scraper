# debug_carrefour_subcategories.py — Script de nomes diagnostic, NO toca
# cap dada ni el scraper de produccio. La primera execucio real del nou
# CarrefourScraper (6.484 productes) mostra que TOTES les categories grans
# s'aturen a offset=1008: Carrefour sembla limitar la paginacio a ~1000
# resultats per llistat (Frescos diu 2.401 productes pero nomes se'n poden
# recorrer 1.011). Aquest script investiga, abans de tocar produccio:
#   1. Que retorna exactament la pagina a offset=1008 (limit o bloqueig?)
#   2. Quines subcategories te cada categoria i quants productes indica
#      cadascuna (si totes tenen < 1000, baixant-hi es cobreix tot)
#   3. La URL correcta de Mascotas (dona 0 productes)
#   4. Les pagines que donen 8 productes en lloc de 24 (carrega parcial?)

import re
import time
from seleniumbase import Driver

BASE = 'https://www.carrefour.es'
GRAELLA = 'ul.product-card-list__list div[data-origin="list"]'


def superar_cloudflare(driver, url):
    for intent in range(3):
        for _ in range(3):
            if 'just a moment' not in driver.get_title().lower():
                return True
            time.sleep(2)
        try:
            driver.uc_gui_click_cf()
            time.sleep(4)
        except Exception:
            pass
        if 'just a moment' not in driver.get_title().lower():
            return True
        driver.uc_open_with_reconnect(url, reconnect_time=8)
        time.sleep(3)
    return False


def scroll_pas_a_pas(driver):
    estable, anterior = 0, -1
    for _ in range(40):
        driver.execute_script('window.scrollBy(0, 600);')
        time.sleep(0.8)
        actual = len(driver.find_elements(GRAELLA))
        al_final = driver.execute_script(
            'return window.innerHeight + window.scrollY >= document.body.scrollHeight - 50;')
        if actual == anterior and al_final:
            estable += 1
            if estable >= 2:
                break
        else:
            estable = 0
        anterior = actual
    return anterior


def obrir(driver, url):
    driver.get(url)
    time.sleep(3)
    return superar_cloudflare(driver, url)


def total_indicat(driver):
    trobats = re.findall(r'(\d[\d\.]*)\s+(?:productos|resultados)', driver.get_page_source())
    valors = [int(t.replace('.', '')) for t in trobats if t.replace('.', '').isdigit()]
    return max(valors) if valors else None


def links_categoria(driver):
    return driver.execute_script("""
        const out = {};
        document.querySelectorAll('a[href]').forEach(a => {
            const h = a.getAttribute('href') || '';
            const m = h.match(/\\/supermercado\\/[^?#]+\\/(cat\\d+)\\/c/);
            if (m) {
                const text = (a.innerText || a.getAttribute('title') || '').trim().replace(/\\s+/g, ' ');
                if (!out[m[1]]) out[m[1]] = {href: h.split('?')[0], text: text.slice(0, 60)};
            }
        });
        return out;
    """)


def text_principal(driver):
    return driver.execute_script(
        "const m = document.querySelector('main') || document.body;"
        "return (m.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 400);")


def main():
    driver = Driver(uc=True, headed=True)
    try:
        url = f'{BASE}/supermercado/frescos/cat20002/c'
        driver.uc_open_with_reconnect(url, reconnect_time=6)
        time.sleep(3)
        superar_cloudflare(driver, url)
        try:
            driver.click('#onetrust-accept-btn-handler', timeout=8)
            time.sleep(2)
        except Exception:
            pass

        # 1. Que hi ha a offset=1008?
        print("\n######## 1. FRESCOS a offset=984 i offset=1008 ########")
        for off in (984, 1008):
            u = f'{BASE}/supermercado/frescos/cat20002/c?offset={off}'
            ok = obrir(driver, u)
            n = scroll_pas_a_pas(driver) if ok else None
            print(f"offset={off}: cloudflare_ok={ok} | titol={driver.get_title()!r} | url_final={driver.current_url}")
            print(f"   targetes a la graella: {n}")
            print(f"   text principal: {text_principal(driver)[:300]!r}")

        # 2. Subcategories de cada categoria gran
        categories = [
            ('frescos', 'cat20002'), ('la-despensa', 'cat20001'), ('bebidas', 'cat20003'),
            ('drogueria-y-limpieza', 'cat20005'), ('perfumeria-e-higiene', 'cat20004'),
        ]
        for nom, codi in categories:
            print(f"\n######## 2. SUBCATEGORIES de {nom} ({codi}) ########")
            u = f'{BASE}/supermercado/{nom}/{codi}/c'
            if not obrir(driver, u):
                print("   ⛔ Cloudflare")
                continue
            total = total_indicat(driver)
            links = links_categoria(driver)
            propis = {k: v for k, v in links.items() if k != codi}
            print(f"   Total indicat: {total} | links de categoria a la pagina: {len(propis)}")
            for k, v in list(propis.items())[:40]:
                print(f"   - {k}: {v['text']!r} -> {v['href']}")

        # 2b. Quants productes indica cada subcategoria de Frescos (mostra)
        print("\n######## 2b. Totals de subcategories de FRESCOS (mostra) ########")
        u = f'{BASE}/supermercado/frescos/cat20002/c'
        obrir(driver, u)
        links = {k: v for k, v in links_categoria(driver).items() if k != 'cat20002'}
        for k, v in list(links.items())[:12]:
            su = BASE + v['href'] if v['href'].startswith('/') else v['href']
            if not obrir(driver, su):
                print(f"   {k}: ⛔ Cloudflare")
                continue
            print(f"   {k} {v['text']!r}: total indicat={total_indicat(driver)} | titol={driver.get_title()!r}")

        # 3. Mascotas
        print("\n######## 3. MASCOTAS ########")
        u = f'{BASE}/supermercado/mascotas/cat20007/c'
        ok = obrir(driver, u)
        n = scroll_pas_a_pas(driver) if ok else None
        print(f"cloudflare_ok={ok} | titol={driver.get_title()!r} | url_final={driver.current_url} | graella={n}")
        print(f"   text principal: {text_principal(driver)[:300]!r}")
        obrir(driver, f'{BASE}/supermercado')
        candidats = {k: v for k, v in links_categoria(driver).items()
                     if 'mascot' in (v['href'] + v['text']).lower()}
        print(f"   Links amb 'mascot' a /supermercado: {candidats}")

        # 4. Pagines amb nomes 8 productes
        print("\n######## 4. LA DESPENSA offset=384 (va donar 8 productes) ########")
        u = f'{BASE}/supermercado/la-despensa/cat20001/c?offset=384'
        if obrir(driver, u):
            n1 = scroll_pas_a_pas(driver)
            time.sleep(3)
            driver.execute_script('window.scrollTo(0, 0);')
            n2 = scroll_pas_a_pas(driver)
            print(f"   graella despres del 1r scroll: {n1} | despres d'un 2n scroll: {n2}")
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
