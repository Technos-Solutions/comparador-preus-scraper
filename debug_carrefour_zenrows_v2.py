# debug_carrefour_zenrows_v2.py — Script de només diagnòstic, NO toca
# cap dada ni el scraper de producció. El diagnostic anterior
# (debug_carrefour_zenrows.py) buscava un selector antic
# ('data-test="search-grid-result"') que ja no existeix a Carrefour.
# Comprovant el context real dels preus trobats, s'ha vist que la
# pagina SI que carrega productes reals amb ZenRows (nomes amb
# js_render=true, sense ni proxy premium), pero amb una estructura
# diferent: <div data-origin="list" app_price="X,XX €"
# app_price_per_unit="Y,YY €" brand="..." catalog="food" ...>.
# Aquest script extreu correctament nom/marca/preu amb aquesta
# estructura real per confirmar que es pot fer servir per produccio.

import os
import re
import requests

API_KEY = os.environ.get('ZENROWS_API_KEY')
URL_CATEGORIA = 'https://www.carrefour.es/supermercado/frescos/cat20002/c'

if not API_KEY:
    print("❌ ZENROWS_API_KEY no trobat a les variables d'entorn")
    exit(1)

params = {
    'url': URL_CATEGORIA,
    'apikey': API_KEY,
    'js_render': 'true',
}

resp = requests.get('https://api.zenrows.com/v1/', params=params, timeout=90)
print(f"Codi HTTP: {resp.status_code}")
html = resp.text
print(f"Mida de la resposta: {len(html)} caracters")

with open('carrefour_zenrows_v2.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Cada 'card' de producte comença amb <div data-origin="list" ...> i te
# diversos atributs en linia. Extraiem el bloc sencer de cada targeta.
targetes = re.findall(r'<div data-origin="list"[^>]*>', html)
print(f"\nTargetes de producte ('data-origin=\"list\"') trobades: {len(targetes)}")

for i, t in enumerate(targetes):
    attrs = dict(re.findall(r'([a-zA-Z_-]+)="([^"]*)"', t))
    print(f"\n[{i}] {attrs}")

# Tambe busquem el nom del producte, que sol anar en un altre element
# proper (h3, span amb classe "product-card__title" o similar).
noms = re.findall(r'class="product-card__title"[^>]*>([^<]*)<', html)
print(f"\nNoms de producte trobats (product-card__title): {len(noms)}")
for n in noms[:10]:
    print(f"  - {n.strip()!r}")

if not noms:
    # Prova alternativa: qualsevol classe que contingui 'title' o 'name'
    # a prop d'una targeta de producte.
    alt = re.findall(r'class="[^"]*(?:title|name)[^"]*"[^>]*>([^<]{3,80})<', html)
    print(f"Alternativa (classes amb 'title'/'name'): {len(alt)} trobades")
    for n in alt[:10]:
        print(f"  - {n.strip()!r}")

print("\n✅ Fet.")
