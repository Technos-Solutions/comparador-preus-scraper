import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

# Provem categories variades per veure casos diferents
categories_test = [115, 420, 221, 181]  # especias, aceite, agua, cerveza

for cat_id in categories_test:
    url = f'https://tienda.mercadona.es/api/categories/{cat_id}/?lang=es&wh=mad1'
    data = requests.get(url, headers=headers).json()
    print(f"\nCategoria {cat_id}:")
    for sub in data.get('categories', [])[:1]:
        for prod in sub.get('products', [])[:3]:
            pi = prod['price_instructions']
            unit_size = pi.get('unit_size', 0)
            size_format = pi.get('size_format', '')
            packaging = prod.get('packaging', '')
            # Calcular quantitat llegible
            if size_format == 'kg':
                quantitat = f"{int(unit_size*1000)} g" if unit_size < 1 else f"{unit_size} kg"
            elif size_format == 'l':
                quantitat = f"{int(unit_size*1000)} ml" if unit_size < 1 else f"{unit_size} l"
            else:
                quantitat = f"{unit_size} {size_format}"
            print(f"  {prod['display_name']}")
            print(f"    envàs={packaging} | quantitat={quantitat} | preu={pi['unit_price']}€")
