import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

# Mirem el camp packaging de diversos productes
url = 'https://tienda.mercadona.es/api/categories/115/?lang=es&wh=mad1'
data = requests.get(url, headers=headers).json()

for sub in data.get('categories', [])[:2]:
    for prod in sub.get('products', [])[:5]:
        packaging = prod.get('packaging', '')
        nom = prod['display_name']
        print(f"  {nom}")
        print(f"    packaging: '{packaging}'")
