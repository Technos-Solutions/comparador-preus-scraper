# Comparador de Preus — Context per Claude Code

## Descripció
Scraper automàtic de preus de supermercats catalans. Executa scrapers setmanalment
via GitHub Actions i guarda ~17.500 productes únics a Google Sheets.
Objectiu final: app de comparació de preus entre supermercats.

## Repositori
https://github.com/Technos-Solutions/comparador-preus-scraper

## Compte
- GitHub: Technos-Solutions
- Gmail: starstech.solution@gmail.com

## Supermercats i estat dels scrapers
| Supermercat    | Estat    | Productes aprox |
|----------------|----------|-----------------|
| Mercadona      | ✅ OK    | ~4.500          |
| Bon Àrea       | ✅ OK    | ~3.000          |
| Dia            | ✅ OK    | ~5.000          |
| Bon Preu/Esclat| ✅ OK    | ~3.500          |
| Carrefour      | ✅ OK    | ~1.500          |

## Arquitectura GitHub Actions (5 workflows sequencials, encadenats amb `workflow_run`)
- **Part 1** (`Scraper_part1.yml`, dilluns 04:00 UTC): Mercadona + Bon Àrea
- **Part 2** (`Scraper_part2.yml`, dilluns 06:00 UTC): Dia
- **Part 3** (`Scraper_part3.yml`, dilluns 08:00 UTC): Bon Preu — Frescos + Alimentació + Begudes
- **Part 4** (`Scraper_part4.yml`, dilluns 13:00 UTC): Bon Preu — Congelats + Làctics + Cura + Neteja + Llar + Mascotes + Nadons + Parafarmàcia
- **Part 5** (`Scraper_part5.yml`, dilluns 18:00 UTC): Carrefour
(dividit en 5 parts per respectar el límit de 6h per job de GitHub Actions; cada part crida `python scraper_main.py --part=N`)

En acabar la Part 5, s'engega automàticament `normalitzador_v2.yml` (via `workflow_run`).

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
- ✅ ~17.500 productes únics funcionant
- ✅ Camps `quantitat` i `envas` afegits a tots els scrapers
- ✅ Workflows ampliats a 5 parts (límit 6h) i encadenats automàticament
- ✅ Normalitzador de noms (Fase 3) implementat amb LLM (v1 Groq, v2 Gemini Flash 2.0 amb caché) — en fase de validació, v1 i v2 conviuen en paral·lel (`Comparacions_v2` vs sortida v1)
- ⏳ **Pendent:** Decidir/consolidar v1 vs v2 del normalitzador un cop validat
- ⏳ **Pendent:** Millorar cobertura de Carrefour (~1.500 vs 5.000+ esperats)
- ⏳ **Pendent:** Front-end Streamlit (no iniciat)

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

## Idioma de treball
Sempre en català. Comentaris del codi en català.
