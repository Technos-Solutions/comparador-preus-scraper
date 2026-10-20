# migrar_historic.py — Un sol cop (20/10): porta l'historic al Google Sheet separat
# "Comparador_Preus_Historic" i esborra la pestanya Historic_Preus del full principal.
# L'historic nomes tenia el punt de partida del 19/10, que es igual que Preus: es refa des
# de Preus amb historic_preus.py i nomes s'esborra la pestanya antiga si quadren les files.

import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import historic_preus


def main():
    historic_preus.main()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    client = gspread.authorize(creds)
    nova = client.open(historic_preus.FULL_HISTORIC).worksheet(historic_preus.PESTANYA).get_all_values()
    principal = client.open(historic_preus.FULL_PRINCIPAL)
    try:
        antiga_ws = principal.worksheet(historic_preus.PESTANYA)
    except gspread.WorksheetNotFound:
        print("La pestanya antiga ja no existeix")
        return
    antiga = antiga_ws.get_all_values()
    print(f"Files (amb capcalera): nova {len(nova)} | antiga {len(antiga)}")
    if len(nova) == len(antiga) and nova[0] == antiga[0] and sorted(map(tuple, nova[1:])) == sorted(map(tuple, antiga[1:])):
        principal.del_worksheet(antiga_ws)
        print("✅ Contingut identic: pestanya Historic_Preus esborrada del full principal")
    else:
        print("⚠️  No quadren: NO s'esborra la pestanya antiga")


if __name__ == '__main__':
    main()
