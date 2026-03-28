import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

# Mirem el contingut d'una subcategoria concreta (Aceite = id 112)
url = 'https://tienda.mercadona.es/api/categories/112/?lang=es&wh=mad1'
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
data = response.json()
print("Claus:", list(data.keys()))
print(json.dumps(data, ensure_ascii=False)[:800])
