# vigilant_cadena.py — Vigila la cadena setmanal (Part 1 -> ... -> Part 5 -> normalitzador v3) i avisa
# si s'atura (INCIDENCIES item 11).
#
# Per que cal: si una part falla, la cadena s'atura en silenci. Casos reals: 09/11 (la Part 3 no va
# arrencar per un error de GitHub) i 16/11 (la Part 2 no va poder instal·lar Chromium); totes dues
# setmanes es va veure dies despres. GitHub no dispara 'workflow_run' quan l'execucio l'ha llancada un
# altre workflow amb GITHUB_TOKEN (com fa la cadena), aixi que el vigilant mira l'estat periodicament.
#
# Que fa a cada comprovacio (workflow vigilant_cadena.yml, cada 2 hores de dilluns a dijous):
#   - Si la part on es troba la cadena ha fallat o s'ha cancel·lat: la torna a llancar UN cop (el que
#     diu CLAUDE.md) i obre un avis. Si torna a fallar, nomes avisa.
#   - Si una part ha acabat be pero la seguent no ha arrencat en 30 min: llanca la seguent un cop i avisa.
#   - Si una part porta mes de 6 h en marxa: avisa (penjada).
#   - Si la Part 1 no ha arrencat en 8 dies: avisa.
#   - Quan el normalitzador acaba be: tanca l'avis obert de la setmana, amb un comentari.
# Els avisos son issues de GitHub amb el titol "[Cadena] ...": GitHub ho notifica per correu i a l'app.
#
# Variables d'entorn: GITHUB_TOKEN, GITHUB_REPOSITORY (owner/repo).
#   DRY_RUN=1  no llanca ni escriu res, nomes diu que faria.
#   ARA=...    (amb DRY_RUN) simula l'estat en una data passada, p. ex. 2026-11-18T08:00:00Z.
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

CADENA = [
    ('Scraper_part1.yml', 'Part 1 (Mercadona + bonÀrea)'),
    ('Scraper_part2.yml', 'Part 2 (Dia)'),
    ('Scraper_part3.yml', 'Part 3 (Bon Preu 1)'),
    ('Scraper_part4.yml', 'Part 4 (Bon Preu 2)'),
    ('Scraper_part5.yml', 'Part 5 (Carrefour)'),
    ('normalitzador_v3.yml', 'Normalitzador v3'),
]
FALLADES = ('failure', 'cancelled', 'timed_out', 'startup_failure', 'action_required', 'stale')
MAX_EN_MARXA = timedelta(hours=6)          # el limit d'un job de GitHub
ESPERA_SEGUENT = timedelta(minutes=30)     # temps maxim perque arrenqui la part seguent
MAX_SENSE_INICI = timedelta(days=8)        # la Part 1 te horari setmanal
PREFIX = '[Cadena]'

API = f"https://api.github.com/repos/{os.environ.get('GITHUB_REPOSITORY', 'Technos-Solutions/comparador-preus-scraper')}"
SESSIO = requests.Session()
SESSIO.headers.update({'Authorization': f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
                       'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
DRY_RUN = os.environ.get('DRY_RUN') == '1'


def data(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00')) if text else None


def execucions(workflow, ara):
    r = SESSIO.get(f"{API}/actions/workflows/{workflow}/runs", params={'branch': 'master', 'per_page': 30})
    r.raise_for_status()
    sortida = []
    for run in r.json().get('workflow_runs', []):
        creat = data(run['created_at'])
        if creat > ara:
            continue
        acabat = data(run['updated_at'])
        # Simulacio d'una data passada: el que encara no havia acabat, estava en marxa
        if run['status'] == 'completed' and acabat <= ara:
            estat, conclusio = 'completed', run['conclusion']
        else:
            estat, conclusio = 'in_progress', None
        sortida.append({'id': run['id'], 'creat': creat, 'inici': data(run.get('run_started_at')) or creat,
                        'acabat': acabat if estat == 'completed' else None, 'estat': estat,
                        'conclusio': conclusio, 'event': run['event'], 'url': run['html_url']})
    return sorted(sortida, key=lambda x: x['creat'])


def issue_oberta(des_de):
    r = SESSIO.get(f"{API}/issues", params={'state': 'open', 'per_page': 50})
    r.raise_for_status()
    for i in r.json():
        if 'pull_request' not in i and i['title'].startswith(PREFIX) and data(i['created_at']) >= des_de:
            return i
    return None


def avisa(titol, cos, des_de):
    oberta = issue_oberta(des_de) if not DRY_RUN else None
    if DRY_RUN:
        print(f"   [prova] AVIS: {PREFIX} {titol}\n           {cos}")
        return
    if oberta:
        SESSIO.post(f"{API}/issues/{oberta['number']}/comments", json={'body': f"**{titol}**\n\n{cos}"}).raise_for_status()
        print(f"   Comentari a l'avis #{oberta['number']}: {titol}")
    else:
        r = SESSIO.post(f"{API}/issues", json={'title': f"{PREFIX} {titol}", 'body': cos})
        r.raise_for_status()
        print(f"   Avis obert #{r.json()['number']}: {titol}")


def rellanca(workflow):
    if DRY_RUN:
        print(f"   [prova] RELLANCARIA {workflow}")
        return
    SESSIO.post(f"{API}/actions/workflows/{workflow}/dispatches", json={'ref': 'master'}).raise_for_status()
    print(f"   Rellançat {workflow}")


def tanca_si_cal(des_de, cos):
    if DRY_RUN:
        print(f"   [prova] Tancaria l'avis obert de la setmana (si n'hi ha): {cos}")
        return
    oberta = issue_oberta(des_de)
    if oberta:
        SESSIO.post(f"{API}/issues/{oberta['number']}/comments", json={'body': cos}).raise_for_status()
        SESSIO.patch(f"{API}/issues/{oberta['number']}", json={'state': 'closed', 'state_reason': 'completed'}).raise_for_status()
        print(f"   Avis #{oberta['number']} tancat")


def comprova(ara):
    print(f"Comprovacio de la cadena: {ara:%Y-%m-%d %H:%M} UTC{' (PROVA, no es fa res)' if DRY_RUN else ''}")
    runs = {wf: execucions(wf, ara) for wf, _ in CADENA}
    part1 = runs['Scraper_part1.yml']
    if not part1:
        print("   No hi ha cap execucio de la Part 1")
        return
    inici = part1[-1]['creat']
    des_de = inici - timedelta(hours=1)
    if ara - inici > MAX_SENSE_INICI:
        avisa("La cadena no ha començat aquesta setmana",
              f"L'ultima Part 1 va començar el {inici:%d/%m %H:%M} UTC. Cal mirar per que no s'ha executat l'horari del dilluns.",
              ara - timedelta(days=1))
        return
    # Execucions de cada pas d'aquesta setmana (des de la ultima Part 1)
    setmana = {wf: [r for r in runs[wf] if r['creat'] >= inici - timedelta(minutes=5)] for wf, _ in CADENA}
    for wf, nom in CADENA:
        estat = setmana[wf][-1] if setmana[wf] else None
        txt = '-' if not estat else (estat['estat'] if estat['estat'] != 'completed' else estat['conclusio'])
        print(f"   {nom:<30} {txt}")
    norm = setmana['normalitzador_v3.yml']
    if norm and norm[-1]['conclusio'] == 'success':
        print("   La cadena d'aquesta setmana ha acabat be")
        tanca_si_cal(des_de, f"✅ La cadena ha acabat be ({norm[-1]['acabat']:%d/%m %H:%M} UTC). Tanco l'avis.")
        return
    # Ultim pas de la cadena que s'ha executat aquesta setmana
    idx = max(i for i, (wf, _) in enumerate(CADENA) if setmana[wf])
    wf, nom = CADENA[idx]
    ultim = setmana[wf][-1]
    if ultim['estat'] != 'completed':
        if ara - ultim['inici'] > MAX_EN_MARXA:
            avisa(f"{nom} porta mes de 6 h en marxa", f"Va començar el {ultim['inici']:%d/%m %H:%M} UTC. Execucio: {ultim['url']}", des_de)
        else:
            print(f"   En marxa: {nom} (des de les {ultim['inici']:%H:%M} UTC). Tot correcte.")
        return
    if ultim['conclusio'] in FALLADES:
        fallades = sum(1 for r in setmana[wf] if r['conclusio'] in FALLADES)
        if fallades == 1:
            rellanca(wf)
            avisa(f"{nom} ha fallat: l'he tornat a llançar",
                  f"Conclusio: {ultim['conclusio']} ({ultim['acabat']:%d/%m %H:%M} UTC). Execucio: {ultim['url']}\n\n"
                  f"L'he rellançat automaticament un cop. Si torna a fallar, avisaré de nou i caldrà mirar-ho.", des_de)
        else:
            avisa(f"{nom} ha tornat a fallar ({fallades} cops): cal revisar-ho",
                  f"Conclusio: {ultim['conclusio']} ({ultim['acabat']:%d/%m %H:%M} UTC). Execucio: {ultim['url']}\n\n"
                  f"No el rellanço més: cal mirar el registre.", des_de)
        return
    # Ha acabat be pero la seguent part no ha arrencat
    if idx + 1 < len(CADENA) and ara - ultim['acabat'] > ESPERA_SEGUENT:
        seg_wf, seg_nom = CADENA[idx + 1]
        rellanca(seg_wf)
        avisa(f"{seg_nom} no ha arrencat: l'he llançat",
              f"{nom} va acabar be el {ultim['acabat']:%d/%m %H:%M} UTC pero la part seguent no va començar.", des_de)
        return
    print(f"   {nom} acaba d'acabar be; la part seguent ha d'arrencar aviat.")


if __name__ == '__main__':
    ara = data(os.environ['ARA']) if os.environ.get('ARA') and DRY_RUN else datetime.now(timezone.utc)
    try:
        comprova(ara)
    except requests.HTTPError as e:
        print(f"Error de l'API de GitHub: {e} {e.response.text[:300]}")
        sys.exit(1)
