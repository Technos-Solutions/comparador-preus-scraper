# migrar_historic.py — Un sol cop (20/10): porta l'historic al Google Sheet separat
# "Comparador_Preus_Historic" i esborra la pestanya Historic_Preus del full principal.
# L'historic ja s'ha refet al full nou amb historic_preus.py (mateix contingut que la pestanya
# antiga, el punt de partida del 19/10). Aqui es compara sense format (valors purs) i nomes
# s'esborra la pestanya antiga si quadren totes les files.

import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import historic_preus


def main():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    client = gspread.authorize(creds)
    full_nou = client.open(historic_preus.FULL_HISTORIC)
    principal = client.open(historic_preus.FULL_PRINCIPAL)
    print(f"Locale: principal {principal.locale} | nou {full_nou.locale}")
    for w in full_nou.worksheets():
        print(f"Full nou, pestanya {w.title!r}: {w.row_count} files x {w.col_count} columnes")
    nova_ws = full_nou.worksheet(historic_preus.PESTANYA)
    antiga_ws = principal.worksheet(historic_preus.PESTANYA)
    nova = nova_ws.get_all_values(value_render_option='UNFORMATTED_VALUE')
    antiga = antiga_ws.get_all_values(value_render_option='UNFORMATTED_VALUE')
    nova_f, antiga_f = nova_ws.get_all_values(), antiga_ws.get_all_values()
    print(f"Files (amb capcalera): nova {len(nova)} | antiga {len(antiga)}")
    print(f"Exemples amb format: nova {nova_f[1:3]} | antiga {antiga_f[1:3]}")
    print(f"Exemples sense format: nova {nova[1:3]} | antiga {antiga[1:3]}")
    diferents = [(x, y) for x, y in zip(sorted(map(tuple, nova[1:]), key=str), sorted(map(tuple, antiga[1:]), key=str)) if x != y]
    print(f"Files diferents (sense format): {len(diferents)}")
    for x, y in diferents[:5]:
        print(f"   nova {x} | antiga {y}")
    if len(nova) == len(antiga) and nova[0] == antiga[0] and not diferents:
        # Pestanya a la mida justa: el full nou nomes ocupa les cel·les que fa servir
        nova_ws.resize(rows=len(nova), cols=len(historic_preus.CAPCALERA))
        principal.del_worksheet(antiga_ws)
        print(f"✅ Contingut identic: pestanya antiga esborrada; full nou ajustat a "
              f"{len(nova)} x {len(historic_preus.CAPCALERA)}")
    else:
        print("⚠️  No quadren: NO s'esborra la pestanya antiga")


if __name__ == '__main__':
    main()
