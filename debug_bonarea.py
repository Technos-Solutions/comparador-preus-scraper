import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Mirem l'estructura d'una categoria (Fruta y verdura = id 1)
url = 'https://tienda.mercadona.es/api/categories/1/'
response = requests.get(url, headers=headers)
data = response.json()

print(f"Categoria: {data['name']}")
print(f"Subcategories: {len(data['categories'])}")
for subcat in data['categories'][:3]:
    print(f"\n  Subcategoria: {subcat['name']} (id={subcat['id']})")
    print(f"  Productes: {len(subcat['products'])}")
    if subcat['products']:
        p = subcat['products'][0]
        print(f"  Exemple: {p['display_name']} -> {p['price_instructions']['unit_price']} EUR")
