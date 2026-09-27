# debug_carrefour_recursiu.py — Script de nomes diagnostic, NO toca cap
# dada (no es connecta a Google Sheets). Valida amb un run real el nou
# CarrefourScraper per subcategories abans de portar-lo a produccio:
#   1. Mira que te la pagina "Baño e Higiene Corporal" (a l'arbre de prova
#      va sortir sense graella, sense total i sense subcategories)
#   2. Executa el CarrefourScraper de scraper_main.py (la mateixa classe,
#      sense importar el modul, que es connecta a Sheets en importar-lo)
#      nomes amb les categories problematiques: Cuidado personal (Baño buit
#      + complement), Mascotas i Bebidas (portades sense graella: Vinos)
#   3. Valida el contingut: productes unics, exemples reals de noms i
#      preus, preus fora de rang i productes sense quantitat

import re
import time
from seleniumbase import Driver as SeleniumBaseDriver

CATEGORIES_PROVA = [
    ('cuidado-personal-e-higiene', 'cat20004'),
    ('mascotas', 'cat20007'),
    ('bebidas', 'cat20003'),
]


def carregar_classe():
    src = open('scraper_main.py', encoding='utf-8').read()
    ini = src.index('class CarrefourScraper:')
    fi = src.index('class BonPreuEsclatScraper:')
    g = {'time': time, 'SeleniumBaseDriver': SeleniumBaseDriver}
    exec(src[ini:fi], g)
    return g['CarrefourScraper']


def inspeccionar_bano(scraper):
    print("\n######## 1. BAÑO E HIGIENE CORPORAL ########")
    # La URL exacta es treu dels links de la categoria mare (no s'endevina)
    mare = 'https://www.carrefour.es/supermercado/cuidado-personal-e-higiene/cat20004/c'
    scraper.driver.get(mare)
    time.sleep(3)
    scraper._superar_cloudflare(mare)
    fills = scraper._subcategories('/supermercado/cuidado-personal-e-higiene')
    print(f"Subcategories de Cuidado personal: {fills}")
    if 'cat20028' not in fills:
        print("⚠️ cat20028 no apareix entre les subcategories")
        return
    url = f"https://www.carrefour.es{fills['cat20028'][0]}/cat20028/c"
    for intent in (1, 2):
        scraper.driver.get(url)
        time.sleep(3)
        ok = scraper._superar_cloudflare(url)
        n = scraper._carregar_tota_la_pagina() if ok else None
        print(f"intent {intent}: cloudflare_ok={ok} | titol={scraper.driver.get_title()!r}")
        print(f"   url_final={scraper.driver.current_url}")
        print(f"   graella={n} | total={scraper._total_categoria()} | "
              f"mida html={len(scraper.driver.get_page_source())}")
        text = scraper.driver.execute_script(
            "const m = document.querySelector('main') || document.body;"
            "return (m.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 400);")
        print(f"   text: {text!r}")
        links = scraper.driver.execute_script("""
            const out = new Set();
            document.querySelectorAll('a[href*="/cat"]').forEach(a => {
                const h = (a.getAttribute('href') || '').split('?')[0];
                if (h.includes('bano') || h.includes('higiene-corporal')) out.add(h);
            });
            return Array.from(out).slice(0, 20);
        """)
        print(f"   links relacionats: {links}")
        if n:
            break


def main():
    C = carregar_classe()
    s = C()
    s.categories = CATEGORIES_PROVA
    s._crear_driver_nou()
    try:
        inspeccionar_bano(s)
    finally:
        s.driver.quit()
        s.driver = None

    print("\n######## 2. SCRAPER PER SUBCATEGORIES ########")
    productes = s.scrape_all()

    print("\n######## 3. VALIDACIO DEL CONTINGUT ########")
    noms = [p['producte'] for p in productes]
    print(f"Productes: {len(productes)} | noms unics: {len(set(noms))}")
    preus = [p['preu'] for p in productes]
    raros = [p for p in productes if not (0.05 <= p['preu'] <= 500)]
    print(f"Preu min={min(preus):.2f} max={max(preus):.2f} | fora de rang (0,05-500): {len(raros)}")
    for p in raros[:5]:
        print(f"   ⚠️ {p['producte']!r} -> {p['preu']}")
    sense_q = [p for p in productes if not p['quantitat']]
    print(f"Sense quantitat detectada: {len(sense_q)}")
    for p in sense_q[:5]:
        print(f"   - {p['producte']!r}")
    for p in productes[::max(1, len(productes) // 15)][:15]:
        print(f"   · {p['producte']!r} | {p['preu']} € | {p['quantitat']!r}")


if __name__ == '__main__':
    main()
