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
        resp = requests.get('https://api.zenrows.com/v1/', params=params, timeout=90)
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
            print(f"  Exemples: {preus_trobats[:5]}")

        articles = re.findall(r'data-test="search-grid-result"', html)
        print(f"Ocurrencies de 'data-test=\"search-grid-result\"' (productes): {len(articles)}")

        nom_fitxer = etiqueta.lower().replace(' ', '_')
        with open(f'carrefour_zenrows_{nom_fitxer}.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML desat a carrefour_zenrows_{nom_fitxer}.html")

        return len(articles) > 0 or len(preus_trobats) > 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# PROVA 1: petició basica, nomes amb renderitzat JS (necessari perque
# Carrefour carrega els productes via una crida interna a una API un cop
# la pagina ja s'ha carregat al navegador).
exit1 = prova('basica_js_render', {'js_render': 'true'})

# PROVA 2: si la basica no funciona, afegim proxy premium (residencial),
# que sol ser el que cal per als llocs amb proteccio anti-bot mes forta
# com Cloudflare Enterprise.
if not exit1:
    prova('premium_proxy', {'js_render': 'true', 'premium_proxy': 'true'})

print("\n✅ Fet.")
