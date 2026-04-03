import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES'
}

url = 'https://tienda.mercadona.es/api/categories/115/?lang=es&wh=mad1'
data = requests.get(url, headers=headers).json()

# Imprimim tots els camps del primer producte
prod = data['categories'][0]['products'][0]
print("TOTS ELS CAMPS:")
print(json.dumps(prod, ensure_ascii=False, indent=2))
