# recategoritzar.py — Re-categoritza productes marcats com "altra" a 'Productes_Normalitzats'
# Pas lleuger: només demana la categoria (no repeteix nom/marca/keywords) per abaratir el cost,
# ja que el nom ja està normalitzat des de normalitzador_v2.py.

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json, os, time

# ── Connexió Google Sheets ────────────────────────────────────────────────────
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_sheets = gspread.authorize(creds)
sheet = client_sheets.open('Comparador_Preus_DB')
ws_cache = sheet.worksheet('Productes_Normalitzats')

print("✅ Connectat a Google Sheets")

# ── Connexió Gemini Flash ─────────────────────────────────────────────────────
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
MODEL_GEMINI = genai.GenerativeModel(
    model_name="gemini-3.5-flash",
    generation_config={"response_mime_type": "application/json", "temperature": 0.1},
)
MIDA_LOT = 100  # lots més grans que el normalitzador: l'output aquí és molt més curt

CATEGORIES = [
    "iogurt", "llet", "beguda_vegetal", "formatge", "embotit", "carn", "peix", "marisc",
    "ous", "mantequilla", "pasta", "arros", "llegum", "cereals", "farina", "sucre", "oli",
    "vinagre", "tomaquet_conserva", "conserva", "sopa", "condiment", "salsa", "melmelada",
    "mel", "pa", "brioixeria", "galeta", "xocolata", "snack", "fruit_sec", "congelat",
    "verdura", "fruita", "cafe", "te", "aigua", "refresc", "suc", "cervesa", "vi", "licor",
    "neteja_llar", "higiene_personal", "cura_personal", "bolquer", "mascota", "parafarmacia",
    "altra",
]

PROMPT_SISTEMA = f"""Ets un expert en categorització de productes de supermercat.

Reps una llista JSON de noms de productes JA NORMALITZATS (en català, sense marca ni quantitat).
Retorna SEMPRE un JSON amb format {{"categories": [...]}} on cada element és la categoria,
en el MATEIX ORDRE que la llista d'entrada.

Tria SEMPRE una categoria d'aquesta llista exacta:
{", ".join(CATEGORIES)}

Fes servir "altra" NOMÉS si de veritat no encaixa en cap altra categoria.
"""

# ── Llegir caché i localitzar productes amb categoria "altra" ────────────────
print("Llegint 'Productes_Normalitzats'...")
files = ws_cache.get_all_values()
capçalera = files[0]
col_categoria = capçalera.index('categoria')       # 0-indexed
col_nom_normalitzat = capçalera.index('nom_normalitzat')

a_recategoritzar = []  # (num_fila_al_sheet, nom_normalitzat)
for i, fila in enumerate(files[1:], start=2):       # fila 2 en endavant (1 = capçalera)
    categoria_actual = fila[col_categoria].strip().lower() if len(fila) > col_categoria else ''
    nom_normalitzat = fila[col_nom_normalitzat].strip() if len(fila) > col_nom_normalitzat else ''
    if categoria_actual == 'altra' and nom_normalitzat:
        a_recategoritzar.append((i, nom_normalitzat))

print(f"   Productes a re-categoritzar: {len(a_recategoritzar)}")

LIMIT = os.environ.get('LIMIT')
if LIMIT:
    a_recategoritzar = a_recategoritzar[:int(LIMIT)]
    print(f"   ⚠️  LIMIT actiu: només es processaran {len(a_recategoritzar)} productes (prova)")

# ── Re-categoritzar amb Gemini Flash en lots ──────────────────────────────────
def recategoritzar_lot(noms: list[str], reintents: int = 3) -> list[str]:
    prompt = PROMPT_SISTEMA + "\n\n" + json.dumps(noms, ensure_ascii=False)
    for intent in range(reintents):
        try:
            resposta = MODEL_GEMINI.generate_content(prompt)
            data = json.loads(resposta.text)
            categories = data.get("categories", [])
            if len(categories) != len(noms):
                print(f"   ⚠️  Gemini ha retornat {len(categories)} en lloc de {len(noms)} — lot descartat")
                return []
            return categories
        except Exception as e:
            missatge = str(e)
            if '429' in missatge:
                espera = 60 * (intent + 1)
                print(f"   ⏳ Rate limit ({missatge[:200]}) — esperant {espera}s (intent {intent+1}/{reintents})...")
                time.sleep(espera)
            else:
                print(f"   ❌ Error Gemini: {e}")
                return []
    print(f"   ❌ Lot descartat després de {reintents} intents")
    return []

LLINDAR_LOTS_FALLITS = 5
lots_fallits_consecutius = 0
actualitzacions = []  # gspread.Cell

if a_recategoritzar:
    print("\nRe-categoritzant amb Gemini Flash...")
    total_lots = -(-len(a_recategoritzar) // MIDA_LOT)
    for i in range(0, len(a_recategoritzar), MIDA_LOT):
        lot = a_recategoritzar[i:i + MIDA_LOT]
        noms = [nom for _, nom in lot]
        num_lot = i // MIDA_LOT + 1
        print(f"   Lot {num_lot}/{total_lots} ({len(lot)} productes)...", end=" ", flush=True)

        categories = recategoritzar_lot(noms)

        if not categories:
            lots_fallits_consecutius += 1
            print("❌ lot descartat")
            if lots_fallits_consecutius >= LLINDAR_LOTS_FALLITS:
                print(f"\n   🛑 {LLINDAR_LOTS_FALLITS} lots seguits han fallat — sembla un problema de fons. Aturant.")
                break
        else:
            lots_fallits_consecutius = 0
            for (num_fila, _), cat in zip(lot, categories):
                actualitzacions.append(gspread.Cell(num_fila, col_categoria + 1, cat.strip()))
            print(f"✅ {len(categories)} recategoritzats")

        if num_lot < total_lots:
            time.sleep(3)

    if actualitzacions:
        print(f"\nActualitzant {len(actualitzacions)} categories a la fulla...")
        bloc = 500
        for i in range(0, len(actualitzacions), bloc):
            ws_cache.update_cells(actualitzacions[i:i + bloc], value_input_option='USER_ENTERED')
            print(f"   {min(i + bloc, len(actualitzacions))}/{len(actualitzacions)} actualitzades...")
        print("   ✅ Caché actualitzada")
else:
    print("   ✅ Cap producte amb categoria 'altra' — res a fer")

print(f"\n✅ Fet! {len(actualitzacions)} productes re-categoritzats.")
