# debug_carrefour_chrome_raw.py — Script de només diagnòstic, NO toca cap
# dada ni el scraper de producció. nodriver amaga l'error real de Chrome
# darrere un missatge generic ("Failed to connect to browser"). Aquest
# script llança Chrome manualment amb els mateixos arguments que fa
# servir nodriver (via la seva pròpia classe Config, sense passar per
# Browser.start()) i imprimeix directament stdout/stderr del procés i el
# codi de sortida, per veure la causa real.

import subprocess
import time
import shutil
import requests

from nodriver.core.config import Config

ruta_chrome = shutil.which('google-chrome') or shutil.which('google-chrome-stable')
print(f"Chrome trobat a: {ruta_chrome}")

config = Config(headless=False, sandbox=False)
args = config()
print(f"Arguments generats per nodriver.Config: {args}")
print(f"Host/Port assignats: {config.host}:{config.port}")

# El host/port normalment es completen dins de Browser.start(); ho fem
# nosaltres manualment igual que fa la llibreria per replicar-ho exacte.
import socket


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


port = free_port()
args.append(f"--remote-debugging-host=127.0.0.1")
args.append(f"--remote-debugging-port={port}")
print(f"Port de depuracio triat manualment: {port}")

cmd = [ruta_chrome] + args
print(f"Comanda completa:\n{' '.join(cmd)}")

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

connectat = False
for intent in range(15):
    time.sleep(1)
    codi_sortida = proc.poll()
    if codi_sortida is not None:
        print(f"\nEl proces ha acabat sol despres de {intent+1}s amb codi: {codi_sortida}")
        break
    try:
        r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=2)
        print(f"\nConnexio OK despres de {intent+1}s: {r.status_code} {r.text[:300]}")
        connectat = True
        break
    except Exception as e:
        print(f"Intent {intent+1}/15: encara no respon ({type(e).__name__})")

if not connectat:
    codi_sortida = proc.poll()
    print(f"\nCodi de sortida final (None = encara actiu): {codi_sortida}")
    proc.terminate()
    time.sleep(1)
    try:
        stdout, stderr = proc.communicate(timeout=5)
        print(f"\n--- STDOUT de Chrome ---\n{stdout.decode(errors='replace')}")
        print(f"\n--- STDERR de Chrome ---\n{stderr.decode(errors='replace')}")
    except Exception as e2:
        print(f"No s'ha pogut llegir stdout/stderr: {e2}")

proc.kill()

print("\nFet.")
