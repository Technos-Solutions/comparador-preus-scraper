# debug_carrefour_zenrows.py — Script de només diagnòstic, NO toca cap
# dada ni el scraper de producció. Prova ZenRows (servei de pagament/pla
# gratuit amb bypass anti-bot) contra una pagina de categoria de
# Carrefour per veure si evita el bloqueig de Cloudflare Enterprise que
# fins ara ha bloquejat totes les proves fetes amb Selenium/SeleniumBase/
# nodriver (tant des de GitHub Actions com des d'una IP residencial real
# via self-hosted runner).

import os
import re
import requests

API_KEY = os.environ.get('ZENROWS_API_KEY')
URL_CATEGORIA = 'https://www.carrefour.es/supermercado/frescos/cat20002/c'

if not API_KEY:
    print("❌ ZENROWS_API_KEY no trobat a les variables d'entorn")
    exit(1)


def prova(etiqueta, params_extra):
    print(f"\n=== {etiqueta} ===")
    params = {
        'url': URL_CATEGORIA,
        'apikey': API_KEY,
    }
    params.update(params_extra)
    try:
        resp = requests.get('https://api.zenrows.com/v1/', params=params, timeout=120)
        print(f"Codi HTTP: {resp.status_code}")
        html = resp.text
        print(f"Mida de la resposta: {len(html)} caracters")

        titol_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        titol = titol_match.group(1).strip() if titol_match else '(sense titol)'
        print(f"Titol de la pagina: {titol!r}")

        paraules_sospitoses = ['captcha', 'robot', 'just a moment', 'access denied',
                                'checking your browser', 'human verification']
        trobades = [p for p in paraules_sospitoses if p in html.lower()]
        print(f"Paraules sospitoses trobades: {trobades if trobades else 'cap'}")

        preus_trobats = re.findall(r'\d+,\d{2}\s*€', html)
        print(f"Ocurrencies de patro de preu (X,XX €) a tot l'HTML: {len(preus_trobats)}")
        if preus_trobats:
            print(f"  Exemples: {preus_trobats[:8]}")

        articles = re.findall(r'data-test="search-grid-result"', html)
        print(f"Ocurrencies de 'data-test=\"search-grid-result\"' (productes): {len(articles)}")

        # Diagnostic extra: quins altres 'data-test' hi ha a la pagina?
        # Si el lloc ha canviat el selector, aixo ens ho dira.
        tots_data_test = set(re.findall(r'data-test="([^"]+)"', html))
        print(f"Total de 'data-test' unics trobats a la pagina: {len(tots_data_test)}")
        rellevants = sorted(t for t in tots_data_test if any(
            k in t.lower() for k in ['result', 'product', 'price', 'grid', 'card', 'item']
        ))
        print(f"  'data-test' que semblen relacionats amb productes: {rellevants[:30]}")

        # Context al voltant d'un parell de preus, per veure si son
        # productes reals o nomes banners/promocions.
        for m in re.finditer(r'\d+,\d{2}\s*€', html):
            inici = max(0, m.start() - 150)
            fi = min(len(html), m.end() + 50)
            print(f"  Context preu {m.group()!r}: ...{html[inici:fi]!r}...")
            break

        nom_fitxer = etiqueta.lower().replace(' ', '_')
        with open(f'carrefour_zenrows_{nom_fitxer}.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML desat a carrefour_zenrows_{nom_fitxer}.html")

        return len(articles) > 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# PROVA 1: petició basica, nomes amb renderitzat JS (necessari perque
# Carrefour carrega els productes via una crida interna a una API un cop
# la pagina ja s'ha carregat al navegador).
exit1 = prova('basica_js_render', {'js_render': 'true'})

# PROVA 2: la prova basica ja evita Cloudflare (titol correcte, preus
# trobats), pero potser la graella de productes encara no s'ha acabat
# de carregar quan ZenRows fa la captura. Afegim una espera addicional.
if not exit1:
    prova('amb_espera', {'js_render': 'true', 'wait': '5000'})

# PROVA 3: si encara no hi ha productes, afegim proxy premium
# (residencial), que sol caldre per als llocs amb proteccio mes forta.
if not exit1:
    prova('premium_proxy', {'js_render': 'true', 'premium_proxy': 'true', 'wait': '5000'})

print("\n✅ Fet.")
