# debug_bonpreu_parts_api.py — Script de nomes diagnostic, NO toca Google Sheets.
#
# Prova a escala real la versio nova de BonPreuEsclatScraper de scraper_main.py
# (lectura dels productes via l'estat de la pagina + l'API interna, 10/10) amb
# les mateixes categories de la Part 3 o la Part 4 (variable PART), sense
# escriure res. Compara amb el metode anterior (28/09: Part 3 ~3.600 i
# Part 4 4.183 productes unics) i mesura el temps (limit del job: 6 h).

import ast
import json
import os
import re
import time
from collections import Counter

from seleniumbase import Driver as SeleniumBaseDriver
from selenium.webdriver.common.by import By

CATEGORIES = {
    '3': ['frescos', 'alimentaci', 'begudes'],
    '4': ['congelats', 'ctics', 'cura', 'neteja', 'per la llar', 'mascotes', 'nadons', 'parafarm'],
}


def carregar_classe():
    # La classe de produccio, llegida del fitxer (importar scraper_main es connecta a Sheets)
    font = open('scraper_main.py', encoding='utf-8-sig').read()
    for node in ast.parse(font).body:
        if isinstance(node, ast.ClassDef) and node.name == 'BonPreuEsclatScraper':
            espai = {'SeleniumBaseDriver': SeleniumBaseDriver, 'By': By, 'time': time, 're': re, 'json': json}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'scraper_main.py', 'exec'), espai)
            return espai['BonPreuEsclatScraper']
    raise RuntimeError('BonPreuEsclatScraper no trobat')


def main():
    part = os.environ.get('PART', '4')
    BonPreuEsclatScraper = carregar_classe()
    scraper = BonPreuEsclatScraper(categories_filtre=CATEGORIES[part])
    inici = time.time()
    productes = scraper.scrape_all()
    minuts = (time.time() - inici) / 60
    unics = {(p['producte'], p['supermercat']): p for p in productes}
    print(f"\n######## Resum Part {part} ########")
    print(f"Productes extrets: {len(productes)} | unics (producte+supermercat): {len(unics)} | temps {minuts:.0f} min")
    print(f"Fulles via API: {scraper.fulles_api} | via DOM: {scraper.fulles_dom} | reinicis: {scraper.reinicis}")
    print(f"Sense quantitat: {sum(1 for p in unics.values() if not p['quantitat'])} | "
          f"marca = 'Bon Preu / Esclat' (sense marca): {sum(1 for p in unics.values() if p['marca'] == 'Bon Preu / Esclat')}")
    print(f"Marques mes frequents: {Counter(p['marca'] for p in unics.values()).most_common(12)}")
    print("Exemples:")
    for p in list(unics.values())[:: max(1, len(unics) // 20)][:20]:
        print(f"   {p['preu']:>7.2f} € | {p['quantitat']:<14} | {p['marca']:<18} | {p['producte']}")


if __name__ == '__main__':
    main()
