# debug_revisio_setmanal.py — Script de nomes diagnostic: NOMES LLEGEIX Google Sheets (no escriu
# enlloc) i no crida Gemini. Revisio setmanal despres de la cadena:
#   1. Comparacions_v3: files, columna "Revisar" i casos coneguts del preu per kg/l (item 26)
#   2. Preus actuals dels productes de la llista de la botiga (revisio_items.json), calculats amb
#      la mateixa regla que normalitzador_v3.comparar. Surten comprimits (gzip + base64) perque el
#      registre de GitHub amaga les claus dels JSON.
import base64
import gzip
import json
import os
from collections import Counter

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import normalitzador_v3 as nv3

CASOS = ('Calabacín Simpl', 'Frambuesa 170', 'Pienso de salmón y trigo para gatos esterilizados Purina One',
         'Pepsi zero azúcar pack 2 botellas 1,75', 'Ron Brugal añejo', 'Lombarda 1 Kg', 'Mini bolas sabor queso')


def quantitat_text(total, unitat):
    if unitat == 'u':
        return f"{nv3.numero_net(round(total, 2))} u"
    gran, petit = ('l', 'ml') if unitat == 'ml' else ('kg', 'g')
    valor = f"{nv3.numero_net(round(total / 1000, 2))} {gran}" if total >= 1000 else f"{nv3.numero_net(round(total))} {petit}"
    return valor.replace('.', ',')


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    preus = nv3.llegir_preus(sheet)
    atributs = nv3.llegir_atributs(sheet.worksheet('Productes_Atributs'))
    ref = nv3.referencies_preu(preus, atributs)

    comp = sheet.worksheet('Comparacions_v3').get_all_values()
    cap, files = comp[0], comp[1:]
    i_rev = cap.index('Revisar') if 'Revisar' in cap else -1
    print(f"Comparacions_v3: {len(files)} files | tipus {dict(Counter(f[0] for f in files))} | "
          f"Revisar: {sum(1 for f in files if i_rev >= 0 and f[i_rev].strip())} | data {Counter(f[-1] for f in files).most_common(2)}")

    def calcula(f):
        a = atributs.get((f['supermercat'], f['producte']))
        if not a or not a['producte']:
            return None
        u, m, un, motiu = nv3.quantitat_comparable(f['producte'], f['quantitat'], a, f['preu'],
                                                   ref.get((a['categoria'], a['unitat'])))
        pu, ue = nv3.preu_unitat(f['preu'], u, m, un)
        return a, (u or 1) * (m or 0), un, pu, ue, motiu

    print("\nCasos coneguts (preu per kg/l amb el codi de master):")
    for text in CASOS:
        for f in preus:
            if text.lower() in f['producte'].lower():
                r = calcula(f)
                if r:
                    a, total, un, pu, ue, motiu = r
                    surt = any(f['producte'] in fila for fila in files)
                    print(f"   {f['supermercat'][:10]:<10} | {f['producte'][:55]:<55} | {f['preu']}€ {f['quantitat']!r} -> "
                          f"{pu and round(pu, 2)} {ue} ({motiu}){' | mes barat en una comparacio' if surt else ''}")

    items = json.load(open('revisio_items.json'))
    index = {(f['supermercat'], f['producte']): f for f in preus}
    sortida, falten = [], []
    for id_, sup, nom in items:
        f = index.get((sup, nom))
        r = f and calcula(f)
        if not r or not r[3]:
            falten.append(f"{sup} | {nom}")
            continue
        a, total, un, pu, ue, motiu = r
        sortida.append([id_, round(f['preu'], 2), f['quantitat'], quantitat_text(total, un), round(pu, 2), ue])
    print(f"\nLlista de la botiga: {len(sortida)}/{len(items)} productes amb preu | no trobats: {len(falten)}")
    for t in falten:
        print('   ', t)
    dades = base64.b64encode(gzip.compress(json.dumps(sortida, ensure_ascii=False).encode())).decode()
    print('\nPREUS_BOTIGA_INICI')
    for i in range(0, len(dades), 20000):
        print(dades[i:i + 20000])
    print('PREUS_BOTIGA_FI')


if __name__ == '__main__':
    main()
