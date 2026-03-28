import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

productes = []
url_cats = 'https://tienda.mercadona.es/api/categories/?lang=es&wh=mad1'
cats = requests.get(url_cats, headers=headers).json()
for cat in cats.get('results', []):
    for subcat in cat.get('categories', []):
        url_sub = f"https://tienda.mercadona.es/api/categories/{subcat['id']}/?lang=es&wh=mad1"
        sub_data = requests.get(url_sub, headers=headers).json()
        for sub2 in sub_data.get('categories', []):
            for prod in sub2.get('products', []):
                try:
                    preu = prod['price_instructions']['unit_price']
                    productes.append(prod['display_name'])
                except:
                    continue
        time.sleep(0.2)

print(f"Total productes Mercadona: {len(productes)}")
print(f"Primers 5: {productes[:5]}")
