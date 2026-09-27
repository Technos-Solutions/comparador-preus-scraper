# debug_carrefour_zenrows_v3.py — Script de només diagnòstic, NO toca
# cap dada ni el scraper de producció. El v2 va confirmar 8 targetes de
# producte reals amb preu i marca (app_price, brand, catalog...), pero
# el nom del producte no s'ha trobat amb el selector 'product-card__title'
# (text buit). Aquest script imprimeix un tros ampli d'HTML al voltant
# d'una targeta sencera per localitzar visualment on es troba realment
# el nom, abans de donar per bona l'extraccio completa.

import os
import re
import requests

API_KEY = os.environ.get('ZENROWS_API_KEY')
URL_CATEGORIA = 'https://www.carrefour.es/supermercado/frescos/cat20002/c'

params = {
    'url': URL_CATEGORIA,
    'apikey': API_KEY,
    'js_render': 'true',
}

resp = requests.get('https://api.zenrows.com/v1/', params=params, timeout=90)
html = resp.text
print(f"Codi HTTP: {resp.status_code}, mida: {len(html)}")

# Trobem la posicio de la primera targeta i n'imprimim un tros gran
# (2500 caracters) per veure tota l'estructura interna (nom, imatge,
# link, etc.)
m = re.search(r'<div data-origin="list"', html)
if m:
    inici = m.start()
    tros = html[inici:inici + 2500]
    print("\n=== TROS D'HTML AL VOLTANT DE LA PRIMERA TARGETA ===\n")
    print(tros)
else:
    print("No s'ha trobat cap targeta de producte")
