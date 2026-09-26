# debug_carrefour_nodriver.py — Script de només diagnòstic, NO toca cap dada
# ni el scraper de producció. Prova 'nodriver' (successor d'undetected-
# chromedriver) en lloc de SeleniumBase. Investigacio (2026): Cloudflare
# Enterprise detecta el protocol CDP en si (la crida 'Runtime.enable' que
# fan Selenium/Playwright/SeleniumBase per sota), no nomes la IP o el mode
# headless - per aixo l'API interna de Carrefour (plp-food-papi) seguia
# rebutjant-nos fins i tot amb Chrome real + Xvfb + IP residencial.
# nodriver parla amb Chrome per CDP directe sense aquesta crida detectable.

import asyncio
import re
import shutil
import nodriver as uc

URL = 'https://www.carrefour.es/supermercado/la-despensa/cat20001/c?offset=0'


def trobar_chrome():
    # browser-actions/setup-chrome posa el binari en una ruta que nodriver
    # no sempre detecta automaticament; el busquem explicitament.
    candidats = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium', 'chrome']
    for nom in candidats:
        ruta = shutil.which(nom)
        if ruta:
            print(f"Chrome trobat amb shutil.which('{nom}'): {ruta}")
            return ruta
    print("No s'ha trobat cap binari de Chrome amb shutil.which")
    return None


async def main():
    ruta_chrome = trobar_chrome()
    browser = await uc.start(headless=False, sandbox=False, browser_executable_path=ruta_chrome)
    page = await browser.get(URL)
    await asyncio.sleep(8)

    try:
        boto = await page.select('#onetrust-accept-btn-handler')
        if boto:
            await boto.click()
            print("Banner de cookies acceptat")
            await asyncio.sleep(3)
    except Exception as e:
        print(f"(no s'ha pogut clicar el banner de cookies: {e})")

    for _ in range(3):
        await page.scroll_down(400)
        await asyncio.sleep(2)
    await asyncio.sleep(5)

    titol = await page.evaluate("document.title")
    html = await page.get_content()

    print(f"Titol de la pagina: {titol!r}")
    print(f"Mida de l'HTML: {len(html)} caracters")

    articles = await page.select_all('article[data-test="search-grid-result"]')
    print(f"Elements 'article[data-test=\"search-grid-result\"]' trobats: {len(articles)}")

    if articles:
        primer = articles[0]
        try:
            nom_el = await primer.query_selector('a[data-test="result-title"]')
            preu_el = await primer.query_selector('div[data-test="result-current-price"]')
            print(f"Exemple de producte: {nom_el.text if nom_el else '?'} - {preu_el.text if preu_el else '?'}")
        except Exception as e:
            print(f"(no s'ha pogut llegir nom/preu: {e})")

    preus_trobats = re.findall(r'\d+,\d{2}\s*€', html)
    print(f"Ocurrencies de patro de preu a tot l'HTML: {len(preus_trobats)}")

    paraules_sospitoses = ['captcha', 'robot', 'blocked', 'just a moment', 'checking your browser']
    trobades = [p for p in paraules_sospitoses if p in html.lower()]
    print(f"Paraules sospitoses trobades: {trobades if trobades else 'cap'}")

    try:
        logs = await page.evaluate("""
            (() => {
                return window.__carrefour_debug_errors__ || 'sense captura d\\'errors JS';
            })()
        """)
    except Exception:
        pass

    await page.save_screenshot('carrefour_nodriver_debug.png')
    with open('carrefour_nodriver_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Captura desada a carrefour_nodriver_debug.png i HTML a carrefour_nodriver_debug.html")

    browser.stop()


if __name__ == '__main__':
    uc.loop().run_until_complete(main())
