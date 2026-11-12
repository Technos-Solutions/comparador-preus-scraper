# Llista d'incidències

Incidències detectades per anar resolent un cop acabada la feina en curs.
Seguir la metodologia de `CLAUDE.md`: primer diagnòstic aïllat, després producció.
Quan se'n resolgui una, moure-la a "Resoltes" amb la data i el commit, sense esborrar-ne el text.

Última revisió: 12/11/2026 (amb el David). Pendents: 20 · Resoltes en aquesta revisió: 11.

## Pendents — prioritat alta

Ordre proposat: 11 (avís si la cadena falla) i 28 (preu de la botiga vs web).

11. **Si una part falla, la cadena s'atura en silenci.** Cal un avís, per exemple un correu o
    una alerta quan una part falla o no s'executa.
    Cas real 09/11: la Part 3 es va marcar com a fallada als 52 s sense que GitHub creés el treball de
    scraping (error de GitHub, no del codi). La cadena va quedar aturada fins que la vam tornar a llançar
    a mà el 10/11 a les 04:01 UTC; Parts 3-5 i normalitzador van acabar bé a les 12:10 UTC.

28. **Preu de la botiga diferent del de la web (Dia)** (David, 12/11). Pizza Dr. Oetker Ristorante
    prosciutto 340 g: web de Dia 3,14 € (el que llegim, correcte), botiga 2,99 € (-5%), sense targeta
    Club Dia ni cartell d'oferta. Hipòtesi: la web de Dia mostra el preu d'una zona o botiga per
    defecte (no li diem el codi postal). Per fer: anotar més casos a la llista de la botiga i provar
    amb un diagnòstic si la web/API de Dia dona preus diferents segons el codi postal (Catalunya).
    Mercadona té el mateix risc: llegim el magatzem de Madrid (wh=mad1). Si es confirma, l'aplicació
    ha d'avisar que els preus són els de la web.

27. **Llegir el preu per kg/l que publica cada supermercat** (idea del 08/11, arran de la captura de
    Carrefour: "18,45 € · 6,59 €/kg"). És obligatori a les etiquetes i a les webs, i seria la millor
    validació del nostre càlcul (i del format). Mercadona: `reference_price`/`bulk_price` de l'API; Bon
    Preu: per mirar a l'API; Carrefour i Dia: text de la graella; bonÀrea: per comprovar. Provar-ho
    amb un diagnòstic aïllat per supermercat abans de tocar els scrapers.
    Compte: el preu per kg del supermercat es calcula amb la seva quantitat, i si aquesta és errònia
    també ho és (Bon Preu "ISDIN Llapis enfortidor d'ungles": web "2.5L (10,78 € per litre)", la capsa
    diu 2,5 ml; confirmat pel David el 08/11). Serveix per contrastar: si web, Gemini i preu per kg del
    supermercat quadren, és fiable; si no, es marca per revisar.
    Revisió del David (08-09/11): Carrefour "Pepsi 1,75 cl" i "Ron Brugal 1,75 cl" mostren el preu per litre
    correcte (0,84 / 0,97 / 21,14 €/l, iguals que el nostre); només el títol està malament: bona font per
    contrastar. bonÀrea ("Ekosan 720 l", "0,00 €/ml") i Bon Preu (ISDIN "2.5L", "10,78 € per litre")
    calculen el seu preu per kg amb la quantitat errònia: no serveixen per contrastar.

24. **Normalitzador v3: es perd el model o la gamma del producte** (detectat pel David, 06/11). Lavazza
    "Qualità Oro" i "Crema e Gusto" queden al mateix grup (`cafè mòlt natural`, Lavazza), perquè el prompt
    diu que no s'hi posin noms de màrqueting. La comparació pot barrejar models diferents d'una marca.
    Proposta: afegir un camp `gamma` (línia o model comercial: Qualità Oro, Crema e Gusto, Zero...) per a
    les marques comercials i tornar a extreure atributs només d'aquests productes (cost estimat ~8 €).
    Mentrestant, el prototip busca al nom real de cada producte i mostra el producte concret.

25. **Guardar la marca d'oferta de cada supermercat** (petició del David, 06/11). Ara les ofertes del
    prototip es dedueixen de l'històric (el preu ha baixat respecte la setmana anterior) i no se sap si
    són temporals. Moltes webs marquen la promoció (preu ratllat, etiqueta, preu anterior). Afegir als
    scrapers dos camps, `oferta` (sí/no o text de la promoció) i `preu_anterior`, i provar-ho supermercat
    per supermercat amb un diagnòstic aïllat (Mercadona no fa ofertes; Bon Preu: dades de l'API;
    Carrefour i Dia: preu ratllat a la graella; bonÀrea: per comprovar). Els preus de soci (Club Dia,
    targetes) queden fora de moment.

## Pendents — prioritat mitjana

12. **Alerta de caiguda de productes per supermercat.** Carrefour va estar setmanes a 0 sense
    que ningú se n'adonés. Proposta: en acabar cada part, comparar el recompte amb la
    setmana anterior i avisar si baixa més d'un 20%.

5. **Deduplicació per nom a `Preus`.** `desduplicar` fa servir la clau (producte, supermercat).
   Productes diferents amb el mateix nom (p. ex. mides diferents) es perden: a la prova de
   Carrefour hi havia 4.208 productes únics per link però només 4.183 noms únics.

23. **Històric de preus: soroll als canvis de format** (primer run real, 27/10: 5.479 files; 2.656 nous,
    1.721 pugen, 721 baixen, 381 canvis de format). La majoria de canvis de format no són reduflació:
    - Mercadona i bonÀrea: fruita i verdura per peça o a granel, amb pes variable cada setmana.
    - Bon Preu: productes amb el mateix nom i mides diferents (Weleda 150 ml / 30 ml); el scraper
      desa un sol producte per nom (veure item 5) i cada setmana pot quedar una mida diferent.
    Al prototip, la reduflació es filtra: menys quantitat amb el mateix preu o més, sense peces ni
    granel (4 casos reals el 27/10, p. ex. suavitzant Bonpreu 80 dosis 2 l → 1,6 l a 1,79 €).
    Pendent: aplicar aquest criteri a `historic_preus.py` i desduplicar Bon Preu per nom + format.

9. **Temps de la Part 5.** El run complet del 27/09 va trigar 3h15 (el límit intern és de 5 h
   i el del job de 6 h). Vigilar-ho: si el catàleg creix, caldrà dividir Carrefour en dues parts.

    **10/11:** la Part 5 ha trigat 3h45 (abans 3h15). Vigilar-ho cada setmana.

7. **Carrefour: algunes pàgines carreguen parcialment** (16 de 24 productes, fins i tot
   després de tornar a fer scroll). Al run complet del 27/09 es van extreure 16.521 productes únics,
   mentre que els llistats en sumen 16.988. Una part de la diferència són productes repetits en diverses
   categories, però n'hi ha de perduts: Aperitivos 533/615, Platos Preparados 222/268, Panadería 359/419.
   Opcions: més espera, un segon reintent o reiniciar el navegador.

18. **Bon Àrea tarda 4h20 i el 85% del que extreu són duplicats.** A la Part 1 del 28/09 es van
    extreure 33.677 productes de Bon Àrea, però en quedaven 9.390 únics amb Mercadona inclòs: 28.779
    duplicats. Recorre subcategories que es repeteixen (`_010`, `_020`...). Si s'evitessin, la Part 1
    seria molt més curta.

8. **Rellançar una part a mà conserva les files antigues.** Cada part llegeix el full temporal anterior,
   hi afegeix els productes nous i treu duplicats quedant-se amb la **primera** aparició, que és la fila vella.
   Si es rellança una part (p. ex. la Part 5 el 27/09, que ja tenia Carrefour d'un run anterior), els preus
   dels productes repetits no s'actualitzen i els productes que ja no existeixen continuen a `Preus`.
   A la cadena setmanal normal no passa, perquè la Part 3 reconstrueix `Preus_Temp` sense Carrefour.
   Solució: abans de combinar, treure del full anterior les files del supermercat que la part torna a
   extreure, o quedar-se amb la fila més nova.

30. **Compreses de Mercadona a 2,35 € per unitat** (detectat el 12/11 validant les claus de variant).
    El preu és el del paquet però no se sap quantes unitats porta, i surt a 2,35 €/u contra 0,04-0,13 €/u
    als altres supermercats. Les comparacions surten marcades a "Revisar" (x60 i x22). Revisar la
    quantitat que dona l'API de Mercadona per a aquests productes.

## Pendents — prioritat baixa o idees

2. **Carrefour: ~1% de productes sense quantitat** (48 de 4.208 a la prova).
   Són noms abreujats que venen així de la web, per exemple `T.CREME.GLOSS.CASTING.600` o
   `ESP.HIDRA-RIZOS EXTRA MARCA200`. Idea: cada targeta té l'atribut `app_price_per_unit`
   (p. ex. "1,37 €/100ml"), i la quantitat es pot deduir com a preu ÷ preu per unitat.
   També serviria per verificar les quantitats extretes del nom.

3. **Carrefour: el camp `marca` sempre val "Carrefour".** Ve fixat al codi, però la targeta
   té l'atribut `brand` amb la marca real (Nenuco, Chivas, Font Vella...).

4. **Carrefour: el camp `envas` sempre és buit.** Es podria omplir a partir de la unitat de
   la quantitat o de `app_price_per_unit`.

13. **Actions de GitHub obsoletes (Node 20):** `actions/checkout@v3/v4`,
    `actions/setup-python@v4/v5` i `browser-actions/setup-chrome@v1` donen avís de
    deprecació. Actualitzar-les abans que deixin de funcionar.

    12/11: els avisos ja diuen que GitHub les força a Node 24; de moment funcionen.

14. **Neteja del repositori:** hi ha molts scripts i workflows de diagnòstic ja acabats
    (ZenRows, nodriver, chrome_raw, bonpreu_*, carrefour_*...). Moure'ls a una carpeta
    `debug/` o esborrar-los.
    - També `rapidfuzz`, que encara surt a `requirements.txt` o en algun workflow i ja no es fa servir.
    - El secret `ZENROWS_API_KEY` i el compte de ZenRows ja no calen.

    També els diagnòstics de novembre (només a la branca de treball): debug_preu_unitat, debug_cerca,
    debug_claus_puntuacio, debug_validar_claus, debug_proves_gamma_sabors, debug_revisio_setmanal...

16. **Front-end:** no iniciat. Proposta (01/10): **GitHub Pages** en lloc de Streamlit. Una pàgina
    estàtica gratuïta al mateix repositori que el workflow regenera en acabar la cadena setmanal.
    Google Sheets continua de base de dades fins que vulguem historial de preus (39.000 files per
    setmana superarien el límit de 10 milions de cel·les en un any); llavors, SQLite o Supabase.
    **12/11:** prototip fet (artifact privat "Comparador de preus", dades del 09/11 amb les regles noves).
    Passos següents: passar-lo a GitHub Pages i fer la consulta legal abans de publicar-lo.

17. **Navegació visual/OCR per a Carrefour** (idea del David): probablement ja no cal, perquè el
    scraping funciona. Es deixa anotada per si Carrefour torna a bloquejar.

    **12/11: proposta de descartar-la** (el scraping de Carrefour funciona).

## Resoltes

### Revisió del 12/11/2026

- **0. Normalitzador v2 aturat per la facturació de Gemini** — Resolta (13/10): crèdits de Gemini recarregats; el v3 (`google.genai`) s'atura net amb errors del compte.
- **1. Carrefour: quantitat mal calculada en packs amb format `NxM`** — Resolta (08/11, 1c7edaf): el normalitzador fa servir el pack que diu el nom ("6x15 g" = 90 g) quan la web només dona una unitat. El scraper no s'ha tocat.
- **6. Auditoria de quantitats a tots els supermercats** — Resolta (08/11): auditoria de quantitats feta a tots els supermercats (incidència 26).
- **10. 05/10: la Part 4 es va cancel·lar sense arrencar** — Resolta (07/10): cas puntual (GitHub no va assignar màquina); rellançada a mà. El problema de fons és la 11.
- **15. Normalitzador:** — Resolta (11/10): ja no cal triar: el normalitzador v3 és l'actiu. Esborrar el v1 i el v2 va amb la 14.
- **19. Poques comparacions: 370 de 13.920 productes** — Resolta (08/10): resolta amb el normalitzador v3: 3.830 comparacions el 08/10 i 5.389 el 12/11.
- **20. 07/10: la Part 4 (Bon Preu) només va extreure 1.304 productes** — Resolta (08/10, e6feb43): es repeteix la categoria principal que dona 0.
- **21. Bon Preu: el scraper només llegeix els primers productes de cada fulla** — Resolta (11/10): Bon Preu es llegeix amb l'estat de la pàgina i l'API interna.
- **22. 19/10: Bon Preu perd fulles senceres quan la sessió es degrada** — Resolta (20/10, d0f0796): qualsevol fulla a 0 reinicia i repeteix el node; confirmat a la cadena del 26/10.
- **26. Normalitzador v3: preu per kg/l mal calculat en alguns productes** — Resolta (08/11, 1c7edaf i c5a805b): preu per kg/l amb la quantitat de la web; confirmat a la cadena del 09/11.
- **29. El mateix producte no es comparava per la marca o la categoria** — Resolta (12/11, cef4414 i 813e044): claus sense puntuació, marques comercials sense categoria i sabors unificats. La gamma continua a la 24.

Text complet de les incidències resoltes en aquesta revisió (historial):

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

1. **Carrefour: quantitat mal calculada en packs amb format `NxM`.**
   `extreure_quantitat` només entén "pack de N unitats de X". Amb "6x15 g" desa
   `15 g` en lloc de `90 g`, i el preu/kg surt 6 vegades més car.
   Exemple real: *"Snack líquido con pollo y taurina para gato Vitakraft 6x15 g."* → `15 g`.
   També hi ha casos ambigus com *"... 6 unidades 80 g"*: no queda clar si els 80 g són el total o el pes de cada unitat.
   Revisar si la funció equivalent dels altres supermercats té el mateix problema.

6. **Auditoria de quantitats a tots els supermercats**, per detectar preus/kg absurds, com ja
   es va fer amb els iogurts en pack de `Comparacions_v2`.

10. **05/10: la Part 4 es va cancel·lar sense arrencar** (GitHub no va assignar cap màquina en
    15 min) i la cadena es va aturar abans de Carrefour. Relançada a mà el 07/10. Reforça la
    necessitat de l'avís de l'incidència 11.
    **Primera setmana amb l'encadenament nou** (28/09, en curs). Fins ara, correcte: Part 1 → Part 2
    → Part 3, un sol cop cadascuna. Nota: GitHub endarrereix l'horari de les 04:00 UTC unes 5-6 h
    (la Part 1 va començar a les 10:24, igual que les setmanes anteriors), així que la Part 5 acaba
    de matinada de dimarts. Pendent de verificar les Parts 4, 5 i el normalitzador.

15. **Normalitzador:** decidir entre la v1 (Groq) i la v2 (Gemini) i eliminar-ne una.

19. **Poques comparacions: 370 de 13.920 productes.** Al run #30, el normalitzador agrupa per
    (categoria, **marca**, nom normalitzat). Només compara productes de la mateixa marca en supermercats
    diferents, i les marques pròpies (Hacendado, Bonpreu, Carrefour...) no es comparen mai entre elles.
    Per a l'app caldrà decidir com comparar genèrics, p. ex. "llet sencera" de qualsevol marca per €/l.
    A més, de 28.919 productes només n'entren 13.920 a la taula: la resta es descarten per la
    categoria "altra", per no tenir quantitat o per unitat incompatible.

20. **07/10: la Part 4 (Bon Preu) només va extreure 1.304 productes** (normalment ~4.300). Neteja de la
    llar, Per la llar, Espai Mascotes, Nadons i Parafarmàcia van sortir a 0 a nivell de categoria
    principal. Causa (diagnòstic 08/10): la sessió es va degradar en començar Neteja i el comptador de
    zeros es posa a 0 a cada categoria principal, així que el reinici no saltava. Amb navegador nou,
    les 5 categories donen 3.133 productes. **Corregit** (commit e6feb43): es repeteix la categoria
    principal que dona 0. A la Part 5, Carrefour "Aceites y vinagres" (cat20066) va sortir buida:
    **revisat l'11/10, no es perd res**. És un enllaç antic del menú d'Alimentación; els olis es recorren
    sencers per la categoria nova "Aceites y vinagres" [cat33207691] (155 de 155). Igualment, "Dulces y
    desayunos" [cat20010] i "Helados" [cat460001] són enllaços antics que mostren el total de tota La
    Despensa (6.456) i no aporten cap producte nou (els dolços són a "Dulce" i "Desayuno", els gelats a
    Congelados). Millora opcional (no urgent): saltar els nodes que indiquen un total igual o més gran que
    el del pare, per no perdre ~10 min paginant-los, i no comptar-los com a incidència.

21. **Bon Preu: el scraper només llegeix els primers productes de cada fulla** (llista virtual). Exemples
    (08/10): packs de llet 21 de 90, estris de cuina 21 de 300, hermètics 10 de 87. Bon Preu té
    probablement diverses vegades els ~7.800 productes que tenim.
    **Solució trobada (diagnòstics debug_bonpreu_api*.py):** cada pàgina de fulla porta a
    `window.__INITIAL_STATE__` tots els ids (`data.products.catalogue.data.productGroups[].products`,
    `totalProducts`) i el detall dels primers 30 (`productEntities`). La resta s'obté amb una sola crida
    `PUT /api/webproductpagews/v6/products` (cos = llista d'ids) des de la pàgina, copiant-ne les
    capçaleres (`x-csrf-token`, `client-route-id`, `page-view-id`, `ecom-request-source`...): 90/90 en
    0,3 s i 300/300 en 0,7 s. Camps: `name`, `brand`, `packSizeDescription` ("6 x 1L"), `price.amount`
    i `unitPrice` (preu per litre/kg/unitat). Una categoria principal es talla a 300 productes, així que cal
    recórrer les fulles. **Portat a scraper_main.py l'11/10** després de la prova completa a la branca
    (debug_bonpreu_parts_api.py): Part 3 7.074 únics (abans ~3.600) en 2h33, Part 4 11.265 (abans 4.183) en
    2h36; ~94% de les fulles via API, la resta via DOM (pendent mirar per què). Es desa la marca real.

22. **19/10: Bon Preu perd fulles senceres quan la sessió es degrada** (Part 3: 6.722 productes, -409
    respecte el 12/10: galetes 0 en lloc de 288, sucres i mels 0 en lloc de 65). Hi ha 31 fulles a 0 a la
    Part 3 i 26 a la Part 4 (whisky escocès, tonyina en oli, gats, maquillatge, dentifrici...). El reinici
    del navegador només salta a la **segona** fulla seguida a 0 i només reintenta aquesta: la primera es
    perd. Proposta: en qualsevol fulla o node a 0, reiniciar i repetir el node (tornant a buscar
    subcategories). Cost estimat: ~30-40 min més entre les Parts 3 i 4 (totes dues per sota de 3h).
    **20/10: corregit i portat a master.** Qualsevol fulla a 0 reinicia el navegador i repeteix el node sencer.
    Prova completa (només lectura, run 39440035812): Part 3 7.509 únics en 139 min (19/10: 6.722; galetes
    i sucres recuperats), Part 4 6.654 en 104 min (19/10: 6.058); 0 fulles via DOM. En aquesta prova la
    sessió gairebé no es va degradar (1-2 reinicis, a la cadena n'hi ha ~30): el reintent només va saltar
    un cop (rosegadors, que segueix a 0). Cal confirmar-ho a la cadena del 26/10.
    **Confirmat a la cadena del 26/10:** 34 reintents a la Part 3 i 27 a la Part 4, totes les fulles
    recuperades (només rosegadors a 0, probablement buida). Part 3 7.511 únics, Part 4 6.670.

26. **Normalitzador v3: preu per kg/l mal calculat en alguns productes** (sospita del David, 08/11;
    auditoria amb l'exportació del 06/11, 45.608 productes). La quantitat total la decideix Gemini i
    queda a la caché per nom, en lloc de fer servir la quantitat de la web de cada setmana.
    - Errors greus (factor ≥ x1,5) en 329 productes; 142 de 5.161 comparacions (2,8%) en tenen algun,
      i en 98 el "més barat" que es mostra és fals. Errors lleus (<50%) en unes 225 comparacions més.
    - Tipus: kg no convertit a g (Carrefour "Calabacín 1,5 kg" → 1.500 €/kg); x10 (Dia "Frambuesa
      170 g" → 1.700 g; "Mini bolas 30 g" → 900 g); càpsules comptades malament (Starbucks 10 ud → 100 u).
    - Caché per nom obsoleta: si el format canvia però el nom no (Mercadona "Nachos Hacendado" 150 → 200 g,
      peces de pes variable de bonÀrea cada setmana), o si dos formats tenen el mateix nom (Bon Preu
      "BONPREU Oli refinat de gira-sol" 1 l i 2 l), el preu/kg queda mal calculat.
    - Al revés, la web no sempre diu el pack (Carrefour "pack 24 latas 33 cl" → quantitat "33 cl"): aquí
      Gemini encerta (555 productes).
    Proposta (sense cost de Gemini, només el codi de `comparar`): quantitat de la web de cada setmana;
    la de Gemini només si la web no en té o si coincideix amb un pack que diu el nom (N x M). Simulació
    amb les dades del 06/11: 0 comparacions amb el més barat erroni (abans 98). La validació en part
    és circular (compara amb la web i el nom); els ~850 productes sense quantitat a la web continuen
    depenent de Gemini.
    **08/11: aplicat a `master`** (commit 1c7edaf, `quantitat_comparable` a `normalitzador_v3.py`). Validat
    amb les dades reals (`debug_preu_unitat.py`): 118 de 5.161 comparacions canvien de supermercat més
    barat, 203 de millor preu per kg/l, +216 comparacions noves (productes per unitats que Gemini havia
    deixat sense mida). Cas que queda malament: errors del nom a la web (Carrefour "Pepsi pack 2
    botellas 1,75 cl", que és 1,75 l). Primer run real: cadena del 09/11.
    **08/11 (2a part, a `master` c5a805b):** errors d'escala de la web. Si web i Gemini es contradiuen
    per x50 o més, es tria la quantitat que dona un preu per kg/l més proper a la mediana de la
    categoria. S'activa en 7 productes, tots errors de la web (Carrefour "Pienso Purina One 2,8 g",
    confirmat pel David a la web: el paquet és de 2,8 kg; "Pepsi/Ron Brugal 1,75 cl", confirmat el 09/11:
    la foto diu 2 x 1,75 L i Carrefour mostra 0,84 €/l, igual que el nostre càlcul; bonÀrea "Ekosan
    720 l"). Queda malament: Bon Preu "ISDIN Llapis enfortidor d'ungles 2,5 l" (cosmètic; la web diu
    2,5 L i la capsa 2,5 ml, confirmat pel David).

29. **El mateix producte no es comparava per la marca o la categoria** (12/11, pizzes Dr. Oetker de Dia).
    "Dr Oetker" i "Dr. Oetker" eren marques diferents, i Gemini havia posat les pizzes de Dia a "altra" i
    les de Bon Preu i Carrefour a "congelat". **Arreglat a `master` (cef4414)**: claus sense puntuacio i
    marques comercials comparades sense categoria. 5.376 comparacions (abans 5.340). Queda pendent:
    sabors amb noms diferents ("mozzarella"/"margarida", "4 formatges"/"quatre formatges").
    **Proves del 12/11** (`debug_proves_gamma_sabors.py`, cafe + congelats + totes les pizzes, 2.423 productes,
    Gemini ~0,12 $ en dues rondes):
    - Gamma nomes afegida (crida a part, sense tocar la resta d'atributs). Regla A (qualsevol gamma diferent
      separa): NEGATIVA, separa 59 comparacions i en perd 20 perque moltes webs no diuen la linia al nom
      (Marcilla "mescla" sense "Gran Aroma"). Regla B (nomes separa si TOTS els productes del grup tenen
      gamma): POSITIVA, separa 16 grups i 13 son correctes (Ristorante / Casa di Mama / Rustica / Pannini,
      Lavazza Oro / Crema e Gusto, Starbucks Blonde / Pike Place, Buitoni Forno di Pietra / La Grandiosa...);
      3 errors (ColaCao "0%" / "Cero", Lotus "Biscoff" / "Biscuit", Ristorante "Piccolissima").
      Cost estimat de la primera passada per a tots els productes de marca: ~1 $. Cal una columna nova
      `gamma` a Productes_Atributs.
    - Sabors amb codi (numeros en lletres, trets sense repetir ni ordre): POSITIU, +7 comparacions, totes
      correctes (pizza 4 formatges de marca blanca a 5 supermercats, 5 formatges, Carte d'Or...). Sense cost.
    - Sabors amb Gemini: MIXT, 17 unificacions, ~13 bones (tonyina/atun, avellana/nocciola, margarida/
      margarita, peperoni/pepperoni) i ~4 dolentes (treu o afegeix trets). Millor un diccionari fix petit
      amb els bons casos.
    **Aplicat a `master` (813e044, 12/11): sabors amb codi + diccionari** (atun/tonno = tonyina, nocciola =
    avellana, platano = plàtan, margarita = margarida, pepperoni = peperoni) i el "+" compta a les claus
    ("talla 4+" no és "talla 4"). Validat: 5.389 comparacions. Queda pendent: la gamma amb la regla B
    (columna nova i ~1 $) i les compreses de Mercadona a 2,35 €/u (paquet sense nombre d'unitats; surten a
    "Revisar").

### Historial: disseny i primers runs del normalitzador v3 (01/10 - 13/10/2026)

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

**Primer run automàtic del v3 a la cadena (13/10, 04:42-05:21 hora local, 39 min):** 15.606 productes
nous (sobretot Bon Preu, que ara llegeix ~18.300 productes amb l'API), 10.246 sense categoria al caché v2.
S'ha aturat a la categoria "altra" (lot 24 de 66) per `402 Your prepayment credits are depleted`:
**s'han acabat els crèdits de Gemini**. El que s'havia fet està desat: 45.832 de 49.444 productes amb
atributs, **5.036 comparacions** (2.677 marca comercial, 2.359 marca blanca). Tokens: entrada 1,7 M,
sortida 0,55 M (~5 €). Queden ~3.600 productes per al proper run (~1,2 €), que es reprenen sols.
- **35 marques blanques "pendent" errònies:** totes són marques de licors (Baileys, Smirnoff, Johnnie
  Walker, Larios, Martini, Chivas Regal...). Gemini ha marcat `marca_blanca=1` a begudes alcohòliques:
  cal posar-les com a "descartada" i revisar el prompt per a aquesta categoria.
- Lots de "altra" (5 a 19) amb exactament 2.085 tokens de sortida cadascun. Diagnòstic
  `debug_marques_altra.py` (13/10): no són files buides; són **1.260 llibres de Bon Preu** (l'API ara
  llegeix també el basar), tots "llibre infantil" sense marca ni mida, i per això les respostes són iguals.
  No es poden comparar (sense mida) i costen ~0,4 €. **Decisió del David (13/10): només menjar i
  neteja (i higiene), res de llibres, joguines, etc.** Des del 13/10 el scraper salta a Bon Preu les
  subcategories de basar de "Per la llar" (llibres, papereria, jocs i joguines, parament, petit
  electrodomèstic, tèxtil, calçat, espelmes, pel foc, aire lliure, bricolatge: ~6.800 productes; en
  queden ambientadors i insecticides) i a Carrefour Calzado, Menaje, Papelería i Bazar (~550).
  `Preus` es refà cada setmana, així que desapareixen al proper run de la cadena.
- El mateix diagnòstic: de 126 marques "pendent", **42 es venen a 2 o més supermercats** (licors,
  Colorcor, Vaseline, Essential, EL NOSTRE...): són de fabricant. Afectaven 179 productes que es
  comparaven com a marca blanca. **Corregit (13/10):** una marca que es ven a 2+ supermercats no és mai
  marca blanca (llevat de les "confirmada"), no s'apunta com a candidata i les "pendent" que ho compleixen
  passen soles a "descartada" (origen "auto: es ven a N supermercats"). El prompt diu que les marques de
  fabricant són sempre 0 i, si dubta, 0.
- Detall: "Deliplus" (confirmada, Mercadona) surt també a Bon Preu en alguns productes (Gemini hi posa
  aquesta marca). No afecta la comparació, però indica marques mal llegides a Bon Preu.

Pendent per al v3:
- ~~Encadenar-lo a la Part 5 en lloc del v2~~ Fet l'11/10: la Part 5 llança el v3; el v2 queda manual.
- Productes sense marca (ous, fruita de Mercadona...) també compten com a marca blanca del supermercat.
- No comparar unitats diferents (€/u amb €/kg).
- Com formar les famílies de candidats a producció (per categoria?) i desar-ne els atributs a la caché.
- Cost real: el run del v2 del 29/09 va normalitzar Carrefour (~15 €). Saldo de Gemini l'01/10: 1,45 €.

### Resoltes abans (setembre 2026)

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
