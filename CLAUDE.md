# Comparador de Preus — Context per Claude Code

## Descripció
Scraper automàtic de preus de supermercats catalans. Executa scrapers setmanalment
via GitHub Actions i guarda ~39.000 productes únics a Google Sheets.
Objectiu final: app de comparació de preus entre supermercats.

## Repositori
https://github.com/Technos-Solutions/comparador-preus-scraper

## Compte
- GitHub: Technos-Solutions
- Gmail: starstech.solution@gmail.com

## Supermercats i estat dels scrapers (27/09/2026)
| Supermercat    | Estat    | Productes aprox | Notes |
|----------------|----------|-----------------|-------|
| Mercadona      | ✅ OK    | (Parts 1+2: 14.581 en total) | |
| Bon Àrea       | ✅ OK    | (inclòs a Parts 1+2) | |
| Dia            | ✅ OK    | (inclòs a Parts 1+2) | |
| Bon Preu/Esclat| ✅ OK    | ~8.000 únics    | SeleniumBase headed + Xvfb; reinici si 2 subcategories seguides a 0 |
| Carrefour      | ✅ OK    | ~16.500 únics   | SeleniumBase headed + Xvfb. Cloudflare bloqueja offset >= 1008: es recorre per subcategories (~3h15) |
Total a `Preus`: 38.990 productes (27/09/2026).

## Arquitectura GitHub Actions (5 workflows en cadena, un sol cop cadascun)
Només la **Part 1** té horari (dilluns 04:00 UTC). Cada part, en acabar amb èxit, llança
la següent amb `workflow_dispatch`, i la Part 5 llança `normalitzador_v2.yml`:
Part 1 → Part 2 → Part 3 → Part 4 → Part 5 → Normalitzador v2.
(Fins al 27/09/2026 cada part tenia també el seu propi horari, i això feia que la Part 5
s'executés fins a 5 cops cada dilluns, amb execucions solapades escrivint als mateixos fulls.
No tornar a posar horaris a les Parts 2-5. Si la cadena es trenca, llançar a mà la part que falta.)
- **Part 1** (`Scraper_part1.yml`): Mercadona + Bon Àrea
- **Part 2** (`Scraper_part2.yml`): Dia
- **Part 3** (`Scraper_part3.yml`): Bon Preu — Frescos + Alimentació + Begudes (~3h)
- **Part 4** (`Scraper_part4.yml`): Bon Preu — Congelats + Làctics + Cura + Neteja + Llar + Mascotes + Nadons + Parafarmàcia (~3h)
- **Part 5** (`Scraper_part5.yml`): Carrefour, per subcategories (~3h15)
(dividit en 5 parts per respectar el límit de 6h per job de GitHub Actions; cada part crida `python scraper_main.py --part=N`)

## Normalitzador de noms de productes (Fase 3 — ✅ implementat, en validació)
Compara el mateix producte entre supermercats normalitzant el nom amb un LLM (no rapidfuzz, tot i que encara apareix a `requirements.txt`/algun workflow de debug).
- **`normalitzador.py`** (v1): primera versió, feta servir Groq com a LLM. Workflow manual `normalitzador.yml`.
- **`normalitzador_v2.py`** (v2, activa): fa servir **Gemini Flash 2.0** (`google-generativeai`), amb caché de resultats a la pestanya `Productes_Normalitzats` per no re-normalitzar productes ja processats, gestió de rate limit (15 RPM, sleep 2–5s entre lots de 50) i aturada neta si s'esgota la quota diària de Gemini. Escriu les comparacions a `Comparacions_v2`. Workflow `normalitzador_v2.yml` (`timeout-minutes: 330`), s'executa automàticament després de la Part 5 o manualment.
- Prompt normalitza a català, format `[producte_base] [variant] [atribut]`, sense marca ni quantitat.
- `debug_bonarea.py` + workflows `debug.yml`/`debug_carrefour.yml`: eines de debug puntual (Bon Àrea/Carrefour), no formen part del flux principal.

## Base de dades — Google Sheets
- Compte: starstech.solution@gmail.com
- Google Sheet: **"Comparador_Preus_DB"**
- Pestanyes (`worksheet`):
  - `Preus` — dades finals consolidades
  - `Preus_Temp`, `Preus_Temp_1`, `Preus_Temp_2` — temporals que fa servir el scraper segons la part
  - `Productes_Normalitzats` — caché del normalitzador v2
  - `Comparacions_v2` — sortida de comparacions de preus normalitzades
- Autenticació: Service Account de Google (secrets de GitHub Actions)

## Camps de cada producte
```
id | producte | marca | supermercat | preu | quantitat | envas | data
```

Exemples:
- `quantitat`: 300, 1, 1.5 (valor numèric)
- `envas`: ml, g, l, kg, u, pack (unitat)
- Permet calcular preu/kg o preu/l per comparar entre supermercats

## Tecnologies
- Python 3.x + Selenium + Chrome (scraping)
- Google Sheets API (`gspread` + `oauth2client`)
- Gemini Flash 2.0 (`google-generativeai`) per normalitzar noms de productes (v2); Groq feia servir la v1
- Streamlit (front-end de l'app) — **encara no iniciat**, no existeix carpeta `streamlit_app/` al repo
- GitHub Actions (automatització setmanal, 5 workflows encadenats)

## Estat actual del projecte
- ✅ ~39.000 productes únics funcionant (27/09/2026: Bon Preu i Carrefour arreglats; Carrefour complet per subcategories)
- ✅ Camps `quantitat` i `envas` afegits a tots els scrapers
- ✅ Workflows ampliats a 5 parts (límit 6h) i encadenats automàticament
- ✅ Normalitzador de noms (Fase 3) implementat amb LLM (v1 Groq, v2 Gemini Flash 2.0 amb caché) — en fase de validació, v1 i v2 conviuen en paral·lel (`Comparacions_v2` vs sortida v1)
- ⏳ **Pendent:** Decidir/consolidar v1 vs v2 del normalitzador un cop validat
- ⏳ **Pendent:** Front-end Streamlit (no iniciat)

**Llista d'incidències pendents: [`INCIDENCIES.md`](INCIDENCIES.md).** Hi s'anota tot el que es detecti
(qualitat de dades, scrapers, automatització) per resoldre-ho quan s'acabi la tasca en curs.

## Fitxers principals
```
comparador-preus-scraper/
├── scraper_main.py            # Scraper principal (tots els supermercats, --part=N)
├── normalitzador.py            # Normalitzador v1 (Groq)
├── normalitzador_v2.py         # Normalitzador v2 (Gemini Flash 2.0 + caché)
├── debug_bonarea.py            # Script de debug puntual
├── requirements.txt
└── .github/workflows/
    ├── Scraper_part1.yml       # Mercadona + Bon Àrea
    ├── Scraper_part2.yml       # Dia
    ├── Scraper_part3.yml       # Bon Preu: Frescos+Alimentació+Begudes
    ├── Scraper_part4.yml       # Bon Preu: Congelats+Làctics+Cura+Neteja+Llar+Mascotes+Nadons+Parafarmàcia
    ├── Scraper_part5.yml       # Carrefour (encadena normalitzador_v2 en acabar)
    ├── normalitzador.yml       # Normalitzador v1, manual
    ├── normalitzador_v2.yml    # Normalitzador v2, manual o auto després de Part 5
    ├── debug.yml               # Debug puntual
    └── debug_carrefour.yml     # Debug puntual Carrefour/Bon Àrea
```
(No hi ha `streamlit_app/` encara — pendent de crear.)

## Secrets de GitHub Actions necessaris
- `GOOGLE_CREDENTIALS` — Service Account de Google Sheets (JSON)
- `SPREADSHEET_ID` — ID del Google Sheet
- `GEMINI_API_KEY` — per al normalitzador v2 (Gemini Flash)
- `GROQ_API_KEY` — per al normalitzador v1 i el workflow de debug de Carrefour

## Metodologia de treball (lliçons apreses — seguir sempre)
1. **El que funciona no es toca.** Qualsevol canvi es prova primer amb un script de
   diagnòstic aïllat (`debug_*.py` + workflow propi, només lectura). Només quan està
   validat amb un run real es porta a `scraper_main.py`.
2. **Validar amb el contingut real, no amb recomptes.** Abans de concloure que una web
   ens bloqueja o que "no hi ha productes", mirar el títol de la pàgina, la mida de
   l'HTML i exemples reals de noms i preus. Els selectors CSS caduquen quan el
   supermercat canvia la web: un recompte de 0 pot ser un selector obsolet, no un
   bloqueig. (Setembre 2026: es van perdre setmanes creient que Cloudflare bloquejava
   Carrefour quan el problema era el selector `article[data-test="search-grid-result"]`,
   que ja no existeix.)
3. **Esgotar les opcions pròpies i gratuïtes abans d'anar a eines externes de pagament**
   (ZenRows, Bright Data...): navegador real en lloc de headless, revisar selectors,
   buscar l'API interna del lloc, reinicis de sessió.
4. **Comprovar a fons cada resultat**, encara que sembli clar, per no fer voltes ni
   repetir feina.
5. Nota tècnica: `workflow_dispatch` només es pot llançar si el fitxer del workflow ja
   existeix a `master` (encara que s'executi sobre una altra branca).

## Idioma de treball
Sempre en català. Comentaris del codi en català.
