# debug_carrefour_arbre.py — Script de nomes diagnostic, NO toca cap dada
# ni el scraper de produccio. Carrefour bloqueja (Cloudflare "Sorry, you
# have been blocked") qualsevol pagina a partir d'offset=1008, aixi que les
# categories de mes de ~1000 productes no es poden recorrer senceres. La
# solucio es baixar a subcategories. Aquest script recorre l'arbre de
# categories obrint NOMES la primera pagina de cada node (sense paginar)
# per validar, abans de tocar produccio:
#   - que la deteccio de subcategories filles funciona a tots els nivells
#   - que totes les fulles tenen <= 1008 productes (recorribles senceres)
#   - que la suma de les fulles quadra amb el total de cada categoria mare
#   - Mascotas i Parafarmacia (portades sense graella) tambe es cobreixen

import re
import time
from seleniumbase import Driver

BASE = 'https://www.carrefour.es'
LIMIT_PAGINACIO = 1008
CATEGORIES = [
    ('frescos', 'cat20002'), ('la-despensa', 'cat20001'), ('bebidas', 'cat20003'),
    ('drogueria-y-limpieza', 'cat20005'), ('cuidado-personal-e-higiene', 'cat20004'),
    ('congelados', 'cat21449123'), ('bebe', 'cat20006'), ('mascotas', 'cat20007'),
    ('parafarmacia', 'cat20008'),
]


def superar_cloudflare(driver, url):
    for _ in range(3):
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


def total_indicat(driver):
    trobats = re.findall(r'(\d[\d\.]*)\s+(?:productos|resultados)', driver.get_page_source())
    valors = [int(t.replace('.', '')) for t in trobats if t.replace('.', '').isdigit()]
    return max(valors) if valors else None


def fills(driver, cami_node):
    """Links de categoria un nivell per sota del node actual
    (cami_node + '/<segment>/catNNN/c')."""
    links = driver.execute_script("""
        const out = [];
        document.querySelectorAll('a[href]').forEach(a => {
            let h = (a.getAttribute('href') || '').split('?')[0].split('#')[0];
            h = h.replace(/^https?:\\/\\/www\\.carrefour\\.es/, '');
            const m = h.match(/^(\\/supermercado\\/.+)\\/(cat\\d+)\\/c$/);
            if (m) out.push([m[1], m[2], (a.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 50)]);
        });
        return out;
    """)
    vistos = {}
    for cami, codi, text in links:
        if cami.startswith(cami_node + '/') and cami.count('/') == cami_node.count('/') + 1:
            vistos.setdefault(codi, (cami, text))
    return vistos


def recorre(driver, cami, codi, nom, nivell, resum):
    url = f'{BASE}{cami}/{codi}/c'
    driver.get(url)
    time.sleep(3)
    if not superar_cloudflare(driver, url):
        print(f"{'  ' * nivell}⛔ {nom}: Cloudflare")
        return 0
    total = total_indicat(driver)
    graella = len(driver.find_elements('ul.product-card-list__list div[data-origin="list"]'))
    subs = fills(driver, cami)
    marca = '' if total is not None and total <= LIMIT_PAGINACIO else '  <-- cal baixar'
    print(f"{'  ' * nivell}{nom} [{codi}] total={total} graella_p1={graella} fills={len(subs)}{marca}")
    if (total is None or total > LIMIT_PAGINACIO) and subs and nivell < 3:
        suma = 0
        for sub_codi, (sub_cami, text) in subs.items():
            suma += recorre(driver, sub_cami, sub_codi, text or sub_cami.split('/')[-1], nivell + 1, resum)
        print(f"{'  ' * nivell}  ↳ suma fulles de {nom}: {suma} (total mare: {total})")
        return suma
    if total is not None and total > LIMIT_PAGINACIO:
        resum['fulles_massa_grans'].append((nom, total))
    if total is None:
        resum['fulles_sense_total'].append((nom, graella))
    resum['fulles'] += 1
    return total or 0


def main():
    driver = Driver(uc=True, headed=True)
    resum = {'fulles': 0, 'fulles_massa_grans': [], 'fulles_sense_total': []}
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
        gran_total = 0
        for slug, codi in CATEGORIES:
            print()
            gran_total += recorre(driver, f'/supermercado/{slug}', codi, slug, 0, resum)
        print(f"\n🏁 Productes coberts (suma de fulles): {gran_total}")
        print(f"   Fulles: {resum['fulles']}")
        print(f"   Fulles > {LIMIT_PAGINACIO} (no es podrien recorrer senceres): {resum['fulles_massa_grans']}")
        print(f"   Fulles sense total detectat: {resum['fulles_sense_total']}")
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
