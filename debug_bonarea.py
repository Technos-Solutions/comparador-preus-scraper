import subprocess
subprocess.run(['pip', 'install', 'requests', '--break-system-packages', '-q'])

import requests
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

url = 'https://tienda.mercadona.es/api/categories/'
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
data = response.json()

print("\nCATEGORIES PRINCIPALS:")
for cat in data['results']:
    print(f"  id={cat['id']} -> {cat['name']}")
