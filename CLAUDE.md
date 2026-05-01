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

## Arquitectura GitHub Actions (3 workflows sequencials)
- **Part 1:** Mercadona + Bon Àrea
- **Part 2:** Dia + Bon Preu/Esclat
- **Part 3:** Carrefour
(dividit en 3 per respectar el límit de 6h per job de GitHub Actions)

## Base de dades — Google Sheets
- Compte: starstech.solution@gmail.com
- Full: "Preus" (dades finals) i "Preus_Temp" (dades temporals del scraper)
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
- Google Sheets API (base de dades)
- Streamlit (front-end de l'app)
- GitHub Actions (automatització setmanal)
- rapidfuzz (normalització de noms de productes, pendent d'implementar)

## Estat actual del projecte
- ✅ ~17.500 productes únics funcionant
- ✅ Camps `quantitat` i `envas` afegits a tots els scrapers
- ✅ Workflows dividits en 3 parts (límit 6h)
- ⏳ **Pendent:** Normalitzador de noms (Fase 3) per comparar el mateix
  producte entre supermercats (ex: "Llet semidesnatada" = tots els supermercats)
- ⏳ **Pendent:** Millorar cobertura de Carrefour (~1.500 vs 5.000+ esperats)

## Fitxers principals
```
comparador-preus-scraper/
├── scraper_main.py          # Scraper principal (tots els supermercats)
├── requirements.txt
├── .github/workflows/
│   ├── scraper_part1.yml    # Mercadona + Bon Àrea
│   ├── scraper_part2.yml    # Dia + Bon Preu/Esclat
│   └── scraper_part3.yml    # Carrefour
└── streamlit_app/           # Front-end (en desenvolupament)
```

## Secrets de GitHub Actions necessaris
- `GOOGLE_CREDENTIALS_JSON` — Service Account de Google Sheets
- `SPREADSHEET_ID` — ID del Google Sheet

## Idioma de treball
Sempre en català. Comentaris del codi en català.
