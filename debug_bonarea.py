import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

# Obtenim totes les categories
url = 'https://tienda.mercadona.es/api/categories/?lang=es&wh=mad1'
data = requests.get(url, headers=headers).json()

total = 0
for cat in data['results']:
    print(f"\n{cat['name']}:")
    for subcat in cat['categories']:
        # Productes de cada subcategoria
        url_sub = f"https://tienda.mercadona.es/api/categories/{subcat['id']}/?lang=es&wh=mad1"
        sub_data = requests.get(url_sub, headers=headers).json()
        prods = sub_data.get('products', [])
        print(f"  {subcat['name']} -> {len(prods)} productes")
        total += len(prods)

print(f"\nTOTAL: {total} productes")
