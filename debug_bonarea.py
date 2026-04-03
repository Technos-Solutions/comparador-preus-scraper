import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

def calcular_quantitat(pi):
    unit_size = pi.get('unit_size', 0)
    size_format = pi.get('size_format', '')
    if size_format == 'kg':
        if unit_size < 1:
            return f"{int(unit_size*1000)} g"
        else:
            val = int(unit_size) if unit_size == int(unit_size) else unit_size
            return f"{val} kg"
    elif size_format == 'l':
        if unit_size < 1:
            return f"{int(unit_size*1000)} ml"
        else:
            val = int(unit_size) if unit_size == int(unit_size) else unit_size
            return f"{val} l"
    else:
        return f"{unit_size} {size_format}".strip()

categories_test = [115, 221, 181, 112]

for cat_id in categories_test:
    url = f'https://tienda.mercadona.es/api/categories/{cat_id}/?lang=es&wh=mad1'
    data = requests.get(url, headers=headers).json()
    print(f"\nCategoria {cat_id}:")
    for sub in data.get('categories', [])[:1]:
        for prod in sub.get('products', [])[:3]:
            pi = prod['price_instructions']
            envàs = prod.get('packaging') or ''
            quantitat = calcular_quantitat(pi)
            print(f"  {prod['display_name']}")
            print(f"    envas={envàs} | quantitat={quantitat} | preu={pi['unit_price']}€")
