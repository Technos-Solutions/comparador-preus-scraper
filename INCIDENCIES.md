# Llista d'incidències pendents

Incidències detectades per anar resolent un cop acabada la feina en curs.
Seguir la metodologia de `CLAUDE.md`: primer diagnòstic aïllat, després producció.
Quan se'n resolgui una, moure-la a "Resoltes" amb la data i el commit.

Última revisió: 01/10/2026

## 🔴 Urgent

0. **Normalitzador v2 aturat per la facturació de Gemini.**
   - 27/09, run #31: `429 Your prepayment credits are depleted`. Hi ha 9.687 productes nous pendents,
     sobretot Carrefour.
   - 28/09: el David hi afegeix 20 € de crèdits, però el diagnòstic `debug_gemini_genai.py` rep
     `429 Your project has exceeded its monthly spending cap`. El projecte té un **límit de despesa
     mensual** que ja s'ha superat. Cal apujar-lo a https://ai.studio/spend o esperar a l'1 d'octubre.
   - Resolt al script (commits 1530b00 i següent): els errors del compte (crèdits, límit de despesa,
     facturació, clau invàlida) aturen el procés al primer lot, i la quota diària es detecta també
     amb "per day".
   - Pendent:
     - Migrar a `google.genai`, que té el mateix format d'error: `ClientError` amb `code`=429 i
       `status`=RESOURCE_EXHAUSTED.
     - Mesurar els tokens per lot per saber el cost real per producte.
     - `CLAUDE.md` diu "Gemini Flash 2.0", però el model configurat és `gemini-3.5-flash`.
       L'estudi de cost inicial era amb el 2.0 i el 3.5 pot ser més car.
   - Historial: els runs #4 a #12 (del 15/06 al 10/08) van arribar tots al límit de temps de 5,5 h,
     amb errors "Illegal header value" (problema amb la clau). Com que la caché només es desa al final,
     aquells runs no van deixar res desat.

## Normalitzador v3 (en disseny, 01/10/2026)

Els diagnòstics del 28/09 i l'01/10 (`debug_gemini_thinking.py`, `debug_mateix_producte.py`) mostren
que el v2 falla per disseny: demana a Gemini un nom lliure en català i després compara text exacte.
Exemple: la Coca-Cola original surt amb 5 noms diferents ("refresc cola", "refresc de cua",
"refresc de cola original"...) i no s'agrupa mai. A més, el nom no és estable entre crides
(28 de 50 iguals) i cada lot de 50 gasta ~6.400 tokens de raonament que no calen.

Mètode nou validat (com ho faria una persona):
- Gemini veu tota una **família de candidats** dels 5 supermercats en una sola crida i en treu
  **atributs**: marca, producte, variant, marca blanca i format (unitats × mida, amb el nom i la
  quantitat de la web).
- Mateix producte = mateixa marca + producte + variant. Coca-Cola: 7 productes comparables entre
  supermercats, amb els €/l correctes (abans Carrefour sortia a 5,49 €/l en lloc de 0,92).
- **Marques blanques**: es comparen entre elles per producte + variant. Llet sencera: Carrefour 0,94,
  Mercadona 0,96, Dia 0,96 i Bon Àrea 0,99 €/l. Llista fixa per supermercat + camp de Gemini.
  Gemini n'ha trobat que no eren a la llista: Casa Juncal (Mercadona), La Almazara del Olivar (Dia),
  De Nuestra Tierra, Simpl i Sensation (Carrefour). Dubtós: "Círculo de Calidad" a Carrefour (és de Lidl?).
- Sense raonament (`thinking_budget=0`) i temperatura 0: els mateixos grups, 1/3 del cost i noms estables.

Prova del v3 a producció (01/10, `debug_normalitzador_v3.py`, categoria llet sencera del v2):
620 productes en 8 lots de 80 barrejant supermercats, amb vocabulari compartit. Vocabulari final:
només 8 productes (llet, batut, crema de llet, llet condensada...). 60 grups de marca comercial
i 26 de marca blanca comparables, 58 i 26 amb productes de lots diferents (el vocabulari funciona
entre crides). Exemple: llet semidesnatada de marca blanca, Carrefour 0,82 €/l, Dia i Mercadona 0,84,
Bon Àrea 0,89. Cost: ~0,33 € per 1.000 productes (resposta compacta) → ~13 € per als 39.000.
Detall a revisar: variants massa fines ("pasteuritzada, sencera" separada de "sencera").

Primer run real del v3 (07/10, llet+oli+aigua, 445 productes, ~0,15 €): 67 comparacions
(42 marca comercial, 25 marca blanca). Revisió del David: correcte en general. Corregit al codi:
agrupació sense accents ("beguda lactia" = "beguda làctia") i columna "Revisar" quan el més car
costa més de 2,5 vegades el més barat (cas real: Puleva amb cereals i fruita, format mal llegit
a Mercadona, 0,33 vs 3,32 €/l). Pendent: variants massa fines ("gust llimona" vs "suc de llimona").

**Primera passada completa del v3 (08/10, 1h15):** 34.953 de 36.070 productes amb atributs,
**3.830 comparacions** (1.971 marca blanca, 1.859 marca comercial), davant les 370 del v2.
Tokens: entrada 3,0 M, sortida 1,43 M (~12 €). Gemini ha proposat 90 marques blanques "pendent"
(n'hi ha de dubtoses: "Essential" a Bon Àrea i Bon Preu, "1601", "Ramblers"...): les ha de revisar el David.
Els ~1.100 productes sense atributs (lots amb respostes incompletes) es reintenten sols al proper run.

Pendent per al v3:
- Encadenar-lo a la Part 5 en lloc del v2 i retirar el v2 (incidència 15).
- Productes sense marca (ous, fruita de Mercadona...) també compten com a marca blanca del supermercat.
- No comparar unitats diferents (€/u amb €/kg).
- Com formar les famílies de candidats a producció (per categoria?) i desar-ne els atributs a la caché.
- Cost real: el run del v2 del 29/09 va normalitzar Carrefour (~15 €). Saldo de Gemini l'01/10: 1,45 €.

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

20. **07/10: la Part 4 (Bon Preu) només va extreure 1.304 productes** (normalment ~4.300). Neteja de la
    llar, Per la llar, Espai Mascotes, Nadons i Parafarmàcia van sortir a 0 a nivell de categoria
    principal. Causa (diagnòstic 08/10): la sessió es va degradar en començar Neteja i el comptador de
    zeros es posa a 0 a cada categoria principal, així que el reinici no saltava. Amb navegador nou,
    les 5 categories donen 3.133 productes. **Corregit** (commit e6feb43): es repeteix la categoria
    principal que dona 0. A la Part 5, Carrefour "Aceites y vinagres" (cat20066) va sortir buida (pendent).

21. **Bon Preu: el scraper només llegeix els primers productes de cada fulla** (llista virtual). Exemples
    (08/10): packs de llet 21 de 90, estris de cuina 21 de 300, hermètics 10 de 87. Bon Preu té
    probablement diverses vegades els ~7.800 productes que tenim.
    **Solució trobada (diagnòstics debug_bonpreu_api*.py):** cada pàgina de fulla porta a
    `window.__INITIAL_STATE__` tots els ids (`data.products.catalogue.data.productGroups[].products`,
    `totalProducts`) i el detall dels primers 30 (`productEntities`). La resta s'obté amb una sola crida
    `PUT /api/webproductpagews/v6/products` (cos = llista d'ids) des de la pàgina, copiant-ne les
    capçaleres (`x-csrf-token`, `client-route-id`, `page-view-id`, `ecom-request-source`...): 90/90 en
    0,3 s i 300/300 en 0,7 s. Camps: `name`, `brand`, `packSizeDescription` ("6 x 1L"), `price.amount`
    i `unitPrice` (preu per litre/kg/unitat). Pendent: portar-ho a scraper_main.py (diagnòstic a escala
    abans) i comprovar si una categoria principal ja dona tots els ids de cop.

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

18. **Bon Àrea tarda 4h20 i el 85% del que extreu són duplicats.** A la Part 1 del 28/09 es van
    extreure 33.677 productes de Bon Àrea, però en quedaven 9.390 únics amb Mercadona inclòs: 28.779
    duplicats. Recorre subcategories que es repeteixen (`_010`, `_020`...). Si s'evitessin, la Part 1
    seria molt més curta.


19. **Poques comparacions: 370 de 13.920 productes.** Al run #30, el normalitzador agrupa per
    (categoria, **marca**, nom normalitzat). Només compara productes de la mateixa marca en supermercats
    diferents, i les marques pròpies (Hacendado, Bonpreu, Carrefour...) no es comparen mai entre elles.
    Per a l'app caldrà decidir com comparar genèrics, p. ex. "llet sencera" de qualsevol marca per €/l.
    A més, de 28.919 productes només n'entren 13.920 a la taula: la resta es descarten per la
    categoria "altra", per no tenir quantitat o per unitat incompatible.

## Automatització i manteniment

10. **05/10: la Part 4 es va cancel·lar sense arrencar** (GitHub no va assignar cap màquina en
    15 min) i la cadena es va aturar abans de Carrefour. Relançada a mà el 07/10. Reforça la
    necessitat de l'avís de l'incidència 11.
    **Primera setmana amb l'encadenament nou** (28/09, en curs). Fins ara, correcte: Part 1 → Part 2
    → Part 3, un sol cop cadascuna. Nota: GitHub endarrereix l'horari de les 04:00 UTC unes 5-6 h
    (la Part 1 va començar a les 10:24, igual que les setmanes anteriors), així que la Part 5 acaba
    de matinada de dimarts. Pendent de verificar les Parts 4, 5 i el normalitzador.

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
16. **Front-end:** no iniciat. Proposta (01/10): **GitHub Pages** en lloc de Streamlit. Una pàgina
    estàtica gratuïta al mateix repositori que el workflow regenera en acabar la cadena setmanal.
    Google Sheets continua de base de dades fins que vulguem historial de preus (39.000 files per
    setmana superarien el límit de 10 milions de cel·les en un any); llavors, SQLite o Supabase.
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
