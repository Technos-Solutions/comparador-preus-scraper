import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

# Obtenim totes les categories principals
url_cats = 'https://tienda.mercadona.es/api/categories/?lang=es&wh=mad1'
data = requests.get(url_cats, headers=headers).json()

total = 0
for cat in data['results']:
    for subcat in cat['categories']:
        url_sub = f"https://tienda.mercadona.es/api/categories/{subcat['id']}/?lang=es&wh=mad1"
        sub_data = requests.get(url_sub, headers=headers).json()
        for sub2 in sub_data.get('categories', []):
            prods = sub2.get('products', [])
            total += len(prods)
            if prods:
                print(f"{cat['name']} > {sub2['name']} -> {len(prods)} productes")

print(f"\nTOTAL: {total} productes")
