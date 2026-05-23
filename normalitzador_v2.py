# normalitzador_v2.py — Normalitzador amb Gemini Flash + caché Google Sheets
# Llegeix de 'Preus', normalitza amb Gemini Flash (caché a 'Productes_Normalitzats'),
# i escriu comparacions a 'Comparacions_v2' per validar en paral·lel amb v1.

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json, os, re, time
from collections import defaultdict, Counter
from datetime import date

# ── Connexió Google Sheets ────────────────────────────────────────────────────
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_sheets = gspread.authorize(creds)
sheet = client_sheets.open('Comparador_Preus_DB')

print("✅ Connectat a Google Sheets")

# ── Connexió Gemini Flash ─────────────────────────────────────────────────────
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
MODEL_GEMINI = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"response_mime_type": "application/json", "temperature": 0.1},
)
MIDA_LOT = 50   # productes per crida a Gemini

# ── Prompt de normalització ───────────────────────────────────────────────────
PROMPT_SISTEMA = """Ets un expert en normalització de productes de supermercat.

Reps una llista JSON de noms de productes (en català o castellà, tal com apareixen als webs dels supermercats).
Retorna SEMPRE un JSON amb format {"productes": [...]} on cada element correspon, en el MATEIX ORDRE, a un nom de la llista d'entrada.

Cada element ha de tenir exactament aquests camps:
{
  "nom_normalitzat": "...",
  "marca": "...",
  "categoria": "...",
  "keywords": "..."
}

━━ REGLES nom_normalitzat ━━
• SEMPRE en CATALÀ
• Format FIXE: [producte_base] [variant] [atribut]
• SENSE marca · SENSE quantitat (g/ml/kg/l/u) · SENSE números
• SENSE informació d'envasat (pack, bric, got, botella, ampolla, tarro)
• Usa formes normalitzades: desnatat (no descremat), sencer (no sencera)

Exemples OBLIGATORIS a seguir fil per randa:
  "DANONE Iogurt Grec Natural 4x125g"      → "iogurt grec natural"
  "Hacendado Yogur Griego 0% 500g"         → "iogurt grec desnatat"
  "YOPLAIT Iogurt Maduixa 4x125g"          → "iogurt maduixa"
  "Danone Yogur Natural Desnatado 4x125g"  → "iogurt natural desnatat"
  "Leche Entera Hacendado 6x1L"            → "llet sencera"
  "Leche Desnatada sin Lactosa Puleva 1L"  → "llet desnatada sense lactosa"
  "Oatly Beguda de Civada 1L"              → "beguda civada"
  "Bebida de Almendras Alpro 1L"           → "beguda ametlla"
  "Estrella Damm Lata 33cl"               → "cervesa lager"
  "Ambar Sin Gluten 33cl"                  → "cervesa sense gluten"
  "Aceite de Oliva Virgen Extra Carbonell" → "oli d'oliva verge extra"
  "Arroz Largo Hacendado 1kg"              → "arròs llarg"
  "Huevos camperos M Eroski 12u"           → "ous campers"

━━ REGLES marca ━━
• Marca comercial real en Title Case (ex: "Danone", "Estrella Damm", "Oatly")
• Marques pròpies de supermercat: Hacendado, Bonpreu, Dia, Carrefour, Ifa
• Si no hi ha marca identificable: ""

━━ CATEGORIES disponibles (tria SEMPRE una) ━━
iogurt · llet · beguda_vegetal · pasta · arros · oli ·
tomaquet_conserva · sucre · farina · mantequilla · ous · cervesa · altra

━━ REGLES keywords ━━
• Inclou (separats per espai, en minúscules):
  - marca (ex: "danone")
  - nom_normalitzat en català (ex: "iogurt grec natural")
  - equivalents principals en castellà (ex: "yogur griego natural")
  - variants comunes si n'hi ha (ex: "dani" per Danone, "estrella" per Estrella Damm)
• Exemples:
  iogurt grec natural / Danone → "danone iogurt yogur grec griego natural dani"
  llet sencera / Hacendado     → "hacendado llet leche entera sencera"
  beguda civada / Oatly        → "oatly civada avena beguda vegetal bebida"
  cervesa lager / Estrella Damm → "estrella damm cervesa cerveza lager"
"""

# ── Llegir Preus ──────────────────────────────────────────────────────────────
print("Llegint productes de 'Preus'...")
ws_preus = sheet.worksheet('Preus')
files = ws_preus.get_all_records()
print(f"   {len(files)} productes llegits")

SUPERMERCATS = ['Mercadona', 'Bon Àrea', 'Dia', 'Bon Preu / Esclat', 'Carrefour']

# ── Llegir caché Productes_Normalitzats ───────────────────────────────────────
print("Llegint caché 'Productes_Normalitzats'...")
try:
    ws_cache = sheet.worksheet('Productes_Normalitzats')
    registres_cache = ws_cache.get_all_records()
    # Diccionari: nom_original (lower strip) → dict amb camps normalitzats
    cache = {
        r['nom_original'].strip(): {
            'nom_normalitzat': r.get('nom_normalitzat', ''),
            'marca':           r.get('marca', ''),
            'categoria':       r.get('categoria', ''),
            'keywords':        r.get('keywords', ''),
        }
        for r in registres_cache
        if r.get('nom_original', '').strip()
    }
    print(f"   {len(cache)} productes a la caché")
except gspread.WorksheetNotFound:
    ws_cache = sheet.add_worksheet(
        title='Productes_Normalitzats', rows=50000, cols=5
    )
    ws_cache.append_row(['nom_original', 'nom_normalitzat', 'marca', 'categoria', 'keywords'])
    cache = {}
    print("   Pestanya 'Productes_Normalitzats' creada (buida)")

# ── Detectar productes nous (no a la caché) ───────────────────────────────────
noms_nous = []
for f in files:
    nom = str(f.get('producte', '')).strip()
    if nom and nom not in cache:
        noms_nous.append(nom)

# Deduplicar mantenint ordre
noms_nous = list(dict.fromkeys(noms_nous))
print(f"\n   Productes nous a normalitzar: {len(noms_nous)}")
print(f"   Crides a Groq necessàries:    {-(-len(noms_nous) // MIDA_LOT)}")  # ceil div

# ── Normalitzar amb Groq en lots ──────────────────────────────────────────────
def normalitzar_lot(noms: list[str], reintents: int = 3) -> list[dict]:
    """
    Envia un lot de ≤50 noms a Gemini Flash. Retorna llista de dicts normalitzats.
    Reintenta automàticament en cas d'error 429 (rate limit per minut).
    """
    prompt = PROMPT_SISTEMA + "\n\n" + json.dumps(noms, ensure_ascii=False)
    for intent in range(reintents):
        try:
            resposta = MODEL_GEMINI.generate_content(prompt)
            data = json.loads(resposta.text)
            productes = data.get("productes", [])
            if len(productes) != len(noms):
                print(f"   ⚠️  Gemini ha retornat {len(productes)} en lloc de {len(noms)} — lot descartat")
                return []
            return productes
        except Exception as e:
            missatge = str(e)
            if '429' in missatge or 'quota' in missatge.lower() or 'rate' in missatge.lower():
                espera = 60 * (intent + 1)   # 60s, 120s, 180s
                print(f"   ⏳ Rate limit — esperant {espera}s (intent {intent+1}/{reintents})...")
                time.sleep(espera)
            else:
                print(f"   ❌ Error Gemini: {e}")
                return []
    print(f"   ❌ Lot descartat després de {reintents} intents")
    return []

nous_normalitzats = []  # llista de [nom_original, nom_normalitzat, marca, categoria, keywords]

if noms_nous:
    print("\nNormalitzant amb Groq...")
    total_lots = -(-len(noms_nous) // MIDA_LOT)
    for i in range(0, len(noms_nous), MIDA_LOT):
        lot = noms_nous[i:i + MIDA_LOT]
        num_lot = i // MIDA_LOT + 1
        print(f"   Lot {num_lot}/{total_lots} ({len(lot)} productes)...", end=" ", flush=True)

        resultat = normalitzar_lot(lot)

        if resultat:
            for nom_orig, norm in zip(lot, resultat):
                entrada = {
                    'nom_normalitzat': norm.get('nom_normalitzat', '').strip(),
                    'marca':           norm.get('marca', '').strip(),
                    'categoria':       norm.get('categoria', 'altra').strip(),
                    'keywords':        norm.get('keywords', '').strip().lower(),
                }
                cache[nom_orig] = entrada
                nous_normalitzats.append([
                    nom_orig,
                    entrada['nom_normalitzat'],
                    entrada['marca'],
                    entrada['categoria'],
                    entrada['keywords'],
                ])
            print(f"✅ {len(resultat)} normalitzats")
        else:
            print("❌ lot descartat")

        # Pausa breu entre lots per no saturar el rate limit per minut
        if num_lot < total_lots:
            time.sleep(2)

    # Guardar nous registres a la caché (Sheets)
    if nous_normalitzats:
        print(f"\nGuardant {len(nous_normalitzats)} nous registres a 'Productes_Normalitzats'...")
        bloc = 500
        for i in range(0, len(nous_normalitzats), bloc):
            ws_cache.append_rows(
                nous_normalitzats[i:i + bloc],
                value_input_option='USER_ENTERED'
            )
        print("   ✅ Caché actualitzada")
else:
    print("   ✅ Tot a la caché — 0 crides a Groq necessàries")

# ── Construir taula de comparacions ──────────────────────────────────────────
print("\nConstruint taula de comparacions...")

def parse_quantitat(quantitat, envas, unitat_cat):
    """Retorna la quantitat en la unitat base de la categoria."""
    try:
        q_str    = str(quantitat).strip()
        env_str  = str(envas).lower().strip()

        if   'kg' in env_str or re.search(r'\d\s*kg', q_str, re.I): unit = 'kg'
        elif 'ml' in env_str or re.search(r'\d\s*ml', q_str, re.I): unit = 'ml'
        elif 'g'  in env_str or re.search(r'\d\s*g\b', q_str, re.I): unit = 'g'
        elif 'l'  in env_str or re.search(r'\d\s*l\b', q_str, re.I): unit = 'l'
        elif any(x in env_str for x in ('u', 'unitat', 'unidad', 'und')): unit = 'u'
        else: return None

        q_net = re.sub(r'[^\d.,x ]', '', q_str).strip()
        q_net = re.sub(r'\s+', ' ', q_net).strip()
        m = re.match(r'(\d+[.,]?\d*)\s*x\s*(\d+[.,]?\d*)', q_net)
        if m:
            total = float(m.group(1).replace(',', '.')) * float(m.group(2).replace(',', '.'))
        else:
            num = re.match(r'(\d+[.,]?\d*)', q_net)
            if not num: return None
            total = float(num.group(1).replace(',', '.'))

        if unitat_cat == 'l':
            if unit == 'ml': return total / 1000
            if unit == 'l':  return total
        elif unitat_cat == 'g':
            if unit in ('g', 'ml'): return total
            if unit == 'kg':        return total * 1000
            if unit == 'l':         return total * 1000
        elif unitat_cat == 'u':
            if unit == 'u': return total
        return None
    except Exception:
        return None

UNITAT_CATEGORIA = {
    'iogurt': 'g', 'llet': 'l', 'beguda_vegetal': 'l',
    'pasta': 'g', 'arros': 'g', 'oli': 'l',
    'tomaquet_conserva': 'g', 'sucre': 'g', 'farina': 'g',
    'mantequilla': 'g', 'ous': 'u', 'cervesa': 'l',
}

taula = []
sense_cache = 0

for f in files:
    nom_orig = str(f.get('producte', '')).strip()
    sup      = f.get('supermercat', '')

    try:
        preu = float(str(f.get('preu', '')).replace(',', '.'))
    except Exception:
        continue

    if nom_orig not in cache:
        sense_cache += 1
        continue

    norm     = cache[nom_orig]
    cat      = norm['categoria']
    if cat == 'altra' or not cat:
        continue

    unitat   = UNITAT_CATEGORIA.get(cat)
    if not unitat:
        continue

    mida     = parse_quantitat(f.get('quantitat', ''), f.get('envas', ''), unitat)
    if not mida:
        continue

    if unitat == 'g':
        preu_per_u = round(preu / mida * 100, 3)   # €/100g
        u_label    = '€/100g'
    elif unitat == 'l':
        preu_per_u = round(preu / mida, 3)          # €/l
        u_label    = '€/l'
    elif unitat == 'u':
        preu_per_u = round(preu / mida, 3)          # €/u
        u_label    = '€/u'

    taula.append({
        'categoria':    cat,
        'supermercat':  sup,
        'marca':        norm['marca'],
        'nom':          norm['nom_normalitzat'],
        'keywords':     norm['keywords'],
        'preu':         preu,
        'mida':         mida,
        'preu_per_u':   preu_per_u,
        'unitat':       unitat,
        'u_label':      u_label,
    })

print(f"   Productes a la taula: {len(taula)}")
if sense_cache:
    print(f"   ⚠️  {sense_cache} productes sense caché (lots fallits?)")

cats = Counter(t['categoria'] for t in taula)
for cat, n in sorted(cats.items()):
    print(f"   {cat:<22} {n:>5}")

# ── Agrupar i comparar per €/unitat ──────────────────────────────────────────
print("\nAgrupant i comparant...")
grups = defaultdict(list)
for t in taula:
    grups[(t['categoria'], t['marca'], t['nom'])].append(t)

files_comp = []
CAPÇALERA = (
    ['Categoria', 'Marca', 'Producte normalitzat', 'Unitat'] +
    SUPERMERCATS +
    ['Preu mínim', 'Supermercat més barat', 'Estalvi', 'Estalvi (%)',
     'Keywords', 'Data actualització']
)

for (cat, marca, nom), entrades in sorted(grups.items()):
    per_sup = defaultdict(list)
    for e in entrades:
        per_sup[e['supermercat']].append(e)

    millors = {s: min(ll, key=lambda x: x['preu_per_u']) for s, ll in per_sup.items()}
    if len(millors) < 2:
        continue

    preus_u   = {s: e['preu_per_u'] for s, e in millors.items()}
    min_pu    = min(preus_u.values())
    max_pu    = max(preus_u.values())
    sup_barat = min(preus_u, key=preus_u.get)
    estalvi   = round(max_pu - min_pu, 3)
    estalvi_pct = round((max_pu - min_pu) / max_pu * 100, 1) if max_pu else 0
    u_label   = list(millors.values())[0]['u_label']
    keywords  = list(millors.values())[0]['keywords']

    fila = [cat, marca or '(marca pròpia)', nom, u_label]
    for sup in SUPERMERCATS:
        fila.append(round(millors[sup]['preu_per_u'], 3) if sup in millors else '')
    fila += [round(min_pu, 3), sup_barat, estalvi, f"{estalvi_pct}%",
             keywords, str(date.today())]
    files_comp.append(fila)

print(f"   Comparacions trobades (≥2 supermercats): {len(files_comp)}")
cats_comp = Counter(f[0] for f in files_comp)
for cat, n in sorted(cats_comp.items()):
    print(f"   {cat:<22} {n:>4}")

# ── Guardar Comparacions_v2 a Google Sheets ───────────────────────────────────
print("\nGuardant a 'Comparacions_v2'...")
try:
    ws_comp = sheet.worksheet('Comparacions_v2')
    ws_comp.clear()
    print("   Pestanya esborrada i neta")
except gspread.WorksheetNotFound:
    ws_comp = sheet.add_worksheet(
        title='Comparacions_v2', rows=10000, cols=len(CAPÇALERA)
    )
    print("   Pestanya 'Comparacions_v2' creada")

ws_comp.append_row(CAPÇALERA)
if files_comp:
    bloc = 500
    for i in range(0, len(files_comp), bloc):
        ws_comp.append_rows(files_comp[i:i + bloc], value_input_option='USER_ENTERED')
        print(f"   Escrites {min(i+bloc, len(files_comp))}/{len(files_comp)} files...")

print(f"\n✅ Fet! {len(files_comp)} comparacions guardades a 'Comparacions_v2'")
print(f"   Crides a Gemini fetes: {-(-len(noms_nous) // MIDA_LOT) if noms_nous else 0}")
print(f"   Productes nous afegits a caché: {len(nous_normalitzats)}")
