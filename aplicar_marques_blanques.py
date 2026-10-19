# aplicar_marques_blanques.py — Actualitza l'estat de marques "pendent" a Marques_Blanques
# amb les comprovacions fetes a internet el 19/10 (aprovades pel David). Nomes toca les
# files indicades (marca + supermercat) que encara estan en "pendent"; no crida Gemini.

import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from normalitzador_v3 import sense_accents

ORIGEN = 'web 19/10'
CANVIS = {
    'confirmada': [
        ('Carrefour', 'Círculo de Calidad'), ('Carrefour', 'Les Cosmétiques'),
        ('Carrefour', 'Nectar Of Bio'), ('Carrefour', 'Forteni'), ('Carrefour', 'Loch Castle'),
        ('Dia', 'Galleteca de Dia'), ('Dia', 'Super Paco'), ('Dia', 'Imaqe'), ('Dia', 'Esos Dias'),
        ("Dia", "Barmon's"), ('Dia', 'Mikanoff'), ('Dia', 'Velero'), ('Dia', 'Burned Barrel'),
        ('Dia', 'Douregal'), ('Mercadona', 'Como tú'), ('Mercadona', 'My Soul'), ('Bon Àrea', 'IYOU'),
    ],
    'descartada': [
        ('Bon Àrea', 'Secretisima'), ('Bon Àrea', 'Bonodor'), ('Bon Àrea', 'Dorlyk'),
        ('Mercadona', 'Convidado de Baco'), ('Bon Àrea', 'Selex'),
        ('Bon Preu / Esclat', 'Intex'), ('Bon Preu / Esclat', 'Campingaz'), ('Bon Preu / Esclat', 'Gre'),
        ('Bon Preu / Esclat', 'Agumay'), ('Bon Preu / Esclat', 'Mister Gadget'),
    ],
}


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    ws = gspread.authorize(creds).open('Comparador_Preus_DB').worksheet('Marques_Blanques')
    files = ws.get_all_records()
    nou_estat = {(s, sense_accents(m)): e for e, ll in CANVIS.items() for s, m in ll}
    actualitzacions, trobades = [], set()
    for i, f in enumerate(files):
        clau = (str(f.get('supermercat', '')).strip(), sense_accents(f.get('marca')))
        if clau in nou_estat and str(f.get('estat', '')).strip().lower() == 'pendent':
            actualitzacions.append({'range': f'C{i + 2}:D{i + 2}', 'values': [[nou_estat[clau], ORIGEN]]})
            trobades.add(clau)
            print(f"   fila {i + 2}: {clau[0]} | {f.get('marca')} -> {nou_estat[clau]}")
    if actualitzacions:
        ws.batch_update(actualitzacions)
    print(f"\nActualitzades: {len(actualitzacions)} de {len(nou_estat)}")
    for clau in sorted(set(nou_estat) - trobades):
        print(f"   ⚠️  no trobada en 'pendent': {clau}")


if __name__ == '__main__':
    main()
