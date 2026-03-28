import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

url = 'https://tienda.mercadona.es/api/categories/1/'
response = requests.get(url, headers=headers)
data = response.json()

# Veiem les claus disponibles
print("Claus:", list(data.keys()))
print("\nContingut (primeres 500 chars):")
print(json.dumps(data, ensure_ascii=False)[:500])
