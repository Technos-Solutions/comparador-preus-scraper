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

config = Config(headless=False)
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

time.sleep(4)

codi_sortida = proc.poll()
print(f"\nCodi de sortida del proces (None = encara actiu): {codi_sortida}")

if codi_sortida is not None:
    stdout, stderr = proc.communicate()
    print(f"\n--- STDOUT de Chrome ---\n{stdout.decode(errors='replace')}")
    print(f"\n--- STDERR de Chrome ---\n{stderr.decode(errors='replace')}")
else:
    print("El proces de Chrome encara esta actiu. Provant de connectar-hi...")
    try:
        r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=5)
        print(f"Resposta de /json/version: {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"Error connectant a /json/version: {e}")
        proc.terminate()
        time.sleep(1)
        try:
            stdout, stderr = proc.communicate(timeout=3)
            print(f"\n--- STDOUT de Chrome (despres de terminate) ---\n{stdout.decode(errors='replace')}")
            print(f"\n--- STDERR de Chrome (despres de terminate) ---\n{stderr.decode(errors='replace')}")
        except Exception as e2:
            print(f"No s'ha pogut llegir stdout/stderr: {e2}")
    proc.kill()

print("\nFet.")
