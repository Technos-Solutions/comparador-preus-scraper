# Llista d'incidències pendents

Incidències detectades per anar resolent un cop acabada la feina en curs.
Seguir la metodologia de `CLAUDE.md`: primer diagnòstic aïllat, després producció.
Quan se'n resolgui una, moure-la a "Resoltes" amb la data i el commit.

Última revisió: 27/09/2026

## Dades (qualitat dels productes)

1. **Carrefour: quantitat mal calculada en packs amb format `NxM`.**
   `extreure_quantitat` només entén "pack de N unitats de X". Amb "6x15 g" desa
   `15 g` en lloc de `90 g`, i el preu/kg surt 6 vegades més car.
   Exemple real: *"Snack líquido con pollo y taurina para gato Vitakraft 6x15 g."* → `15 g`.
   També hi ha casos ambigus com *"... 6 unidades 80 g"*: no queda clar si els 80 g són el total o el pes de cada unitat.
   Revisar si la funció equivalent dels altres supermercats té el mateix problema.

2. **Carrefour: ~1% de productes sense quantitat** (48 de 4.208 a la prova).
   Són noms abreujats que venen així de la web, per exemple `T.CREME.GLOSS.CASTING.600` o
   `ESP.HIDRA-RIZOS EXTRA MARCA200`. Idea: cada targeta té l'atribut `app_price_per_unit`
   (p. ex. "1,37 €/100ml"), i la quantitat es pot deduir com a preu ÷ preu per unitat.
   També serviria per verificar les quantitats extretes del nom.

3. **Carrefour: el camp `marca` sempre val "Carrefour".** Ve fixat al codi, però la targeta
   té l'atribut `brand` amb la marca real (Nenuco, Chivas, Font Vella...).

4. **Carrefour: el camp `envas` sempre és buit.** Es podria omplir a partir de la unitat de
   la quantitat o de `app_price_per_unit`.

5. **Deduplicació per nom a `Preus`.** `desduplicar` fa servir la clau (producte, supermercat).
   Productes diferents amb el mateix nom (p. ex. mides diferents) es perden: a la prova de
   Carrefour hi havia 4.208 productes únics per link però només 4.183 noms únics.

6. **Auditoria de quantitats a tots els supermercats**, per detectar preus/kg absurds, com ja
   es va fer amb els iogurts en pack de `Comparacions_v2`.

## Scrapers

7. **Carrefour: algunes pàgines carreguen parcialment** (16 de 24 productes, fins i tot
   després de tornar a fer scroll). Al run complet del 27/09 es van extreure 16.521 productes únics,
   mentre que els llistats en sumen 16.988. Una part de la diferència són productes repetits en diverses
   categories, però n'hi ha de perduts: Aperitivos 533/615, Platos Preparados 222/268, Panadería 359/419.
   Opcions: més espera, un segon reintent o reiniciar el navegador.

8. **Rellançar una part a mà conserva les files antigues.** Cada part llegeix el full temporal anterior,
   hi afegeix els productes nous i treu duplicats quedant-se amb la **primera** aparició, que és la fila vella.
   Si es rellança una part (p. ex. la Part 5 el 27/09, que ja tenia Carrefour d'un run anterior), els preus
   dels productes repetits no s'actualitzen i els productes que ja no existeixen continuen a `Preus`.
   A la cadena setmanal normal no passa, perquè la Part 3 reconstrueix `Preus_Temp` sense Carrefour.
   Solució: abans de combinar, treure del full anterior les files del supermercat que la part torna a
   extreure, o quedar-se amb la fila més nova.

9. **Temps de la Part 5.** El run complet del 27/09 va trigar 3h15 (el límit intern és de 5 h
   i el del job de 6 h). Vigilar-ho: si el catàleg creix, caldrà dividir Carrefour en dues parts.

## Automatització i manteniment

10. **Primera setmana amb l'encadenament nou** (Part 1 → … → Part 5 → Normalitzador, un sol
    cop cadascuna). Verificar dilluns 28/09 que cada part s'executa una sola vegada i que la
    cadena arriba fins al normalitzador.

11. **Si una part falla, la cadena s'atura en silenci.** Cal un avís, per exemple un correu o
    una alerta quan una part falla o no s'executa.

12. **Alerta de caiguda de productes per supermercat.** Carrefour va estar setmanes a 0 sense
    que ningú se n'adonés. Proposta: en acabar cada part, comparar el recompte amb la
    setmana anterior i avisar si baixa més d'un 20%.

13. **Actions de GitHub obsoletes (Node 20):** `actions/checkout@v3/v4`,
    `actions/setup-python@v4/v5` i `browser-actions/setup-chrome@v1` donen avís de
    deprecació. Actualitzar-les abans que deixin de funcionar.

14. **Neteja del repositori:** hi ha molts scripts i workflows de diagnòstic ja acabats
    (ZenRows, nodriver, chrome_raw, bonpreu_*, carrefour_*...). Moure'ls a una carpeta
    `debug/` o esborrar-los.
    - També `rapidfuzz`, que encara surt a `requirements.txt` o en algun workflow i ja no es fa servir.
    - El secret `ZENROWS_API_KEY` i el compte de ZenRows ja no calen.

## Producte

15. **Normalitzador:** decidir entre la v1 (Groq) i la v2 (Gemini) i eliminar-ne una.
16. **Front-end Streamlit:** no iniciat.
17. **Navegació visual/OCR per a Carrefour** (idea del David): probablement ja no cal, perquè el
    scraping funciona. Es deixa anotada per si Carrefour torna a bloquejar.

## Resoltes

- 26/09/2026 — Bon Preu donava 0 productes: "Human Verification" en mode headless.
  Arreglat amb SeleniumBase (Chrome real) + Xvfb, i reinici del navegador si surten 2
  subcategories seguides a 0.
- 27/09/2026 — Carrefour donava 0 productes: el selector havia caducat i Cloudflare bloquejava
  el mode headless. Arreglat amb SeleniumBase + selectors nous (commit c957cd0).
- 27/09/2026 — Carrefour quedava limitat a 1.008 productes per categoria: Cloudflare bloqueja
  a partir d'aquest offset. Ara es recorre per subcategories (commit 3354f7a).
- 27/09/2026 — La Part 5 s'executava fins a 5 cops cada dilluns: cada part tenia horari propi
  i també la llançava la part anterior. Ara només té horari la Part 1 (commit bdab5a1).
- 27/09/2026 — Primer run complet de Carrefour per subcategories: 16.521 productes únics en 3h15.
  La Part 5 ha llançat el normalitzador sola. `Preus`: 38.990 productes.
- 27/09/2026 — Conservas: les subcategories sumaven 1.091 de 1.194. El "complement" (recórrer també la
  categoria mare) n'ha recuperat 70.
