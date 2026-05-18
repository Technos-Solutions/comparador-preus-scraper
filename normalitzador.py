# normalitzador.py — Compara preus de productes entre supermercats
# Llegeix de 'Preus' i escriu comparacions a 'Comparacions' (Google Sheets)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os, re
from collections import defaultdict, Counter
from datetime import date

# ── Connexió Google Sheets ────────────────────────────────────────────────────
creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws_preus = sheet.worksheet('Preus')

print("✅ Connectat a Google Sheets")
files = ws_preus.get_all_records()
print(f"   {len(files)} productes llegits\n")

SUPERMERCATS = ['Mercadona', 'Bon Àrea', 'Dia', 'Bon Preu / Esclat', 'Carrefour']

# ── Definició de categories ───────────────────────────────────────────────────
CATEGORIES = {
    'llet': {
        'unitat': 'l',
        'inclou': ['leche ', 'llet '],
        'tipus': ['entera', 'sencera', 'desnat', 'semidenat', 'semidesnat',
                  'fresca', 'sense lactosa', 'sin lactosa', 'calcio', 'calci',
                  'omega 3', 'ecològica', 'ecológica', 'barista', 'proteina'],
        'exclou': ['yogur', 'iogurt', 'bífidus', 'bifidus', 'queso', 'formatge',
                   'bebida', 'condensada', 'polvo', 'pols', 'fermentada', 'kéfir',
                   'chocolate', 'xocolata', 'café', 'cafè', 'cacao', 'galleta',
                   'barrita', 'cereal', 'arroz', 'arròs', 'natilla', 'helado',
                   'gelat', 'dulce de leche', 'dolç de llet', 'bollería',
                   'bizcocho', 'pan ', 'pa ', 'pastel', 'brownie', 'salchicha',
                   'solar', 'corporal', 'facial', 'fps', 'spf', 'gel ', 'jabón',
                   'sabó', 'dentífric', 'champú', 'gat', 'gos', 'felix ',
                   'ametll', 'coco', 'avena', 'civada', 'soja', 'vegetal',
                   'nata', 'evaporada', 'crema ', 'puré', 'batut', 'batido',
                   'infantil', 'lactant', 'creixement', 'crecimiento', 'materna',
                   'folic', 'nous'],
    },
    'iogurt': {
        'unitat': 'g',
        'inclou': ['yogur', 'iogurt', 'iogur'],
        'tipus': [],
        'exclou': ['bizcocho', 'bescuit', 'tortita', 'coqueta', 'barqueta',
                   'galleta', 'barrita', 'sandwich', 'snack', 'salsa',
                   'tzatziki', 'helado', 'gelat', 'polo', 'mousse', 'flan',
                   'natilla', 'pastís', 'pastis', 'lingot', 'queso', 'formatge',
                   'papilla', 'puré', 'bolsita', 'tarrito', 'danonino',
                   'baby ', 'bebé', '6 meses', '8 meses', '12 meses', 'smileat',
                   'corporal', 'facial', 'gel ', 'jabón', 'sabó', 'champú',
                   'dosificador', 'gat', 'gos', 'rosegador', 'vitakraft'],
    },
    'pasta': {
        'unitat': 'g',
        'inclou': ['espagueti', 'spaghetti', 'macarró', 'macarron', 'tallarí',
                   'tallarin', 'penne', 'fusill', 'rigatoni', 'farfalle',
                   'linguine', 'fideu', 'fideos', 'lasaña', 'lasanya',
                   'canelons', 'canelones'],
        'tipus': [],
        'exclou': ['salsa', 'sopa', 'plato preparat', 'conserva', 'llauna',
                   'brou', 'caldo'],
    },
    'arros': {
        'unitat': 'g',
        'inclou': ['arroz ', 'arròs '],
        'tipus': [],
        'exclou': ['llet', 'leche', 'postre', 'pastís', 'galeta', 'galleta',
                   'cereal', 'barretes', 'tortita', 'coqueta', 'sopa', 'caldo',
                   'brou', 'plato preparat'],
    },
    'oli': {
        'unitat': 'l',
        'inclou': ['aceite ', 'oli '],
        'tipus': ['oliva', 'girasol', 'gira-sol', 'vegetal'],
        'exclou': ['pescado', 'peix', 'càpsula', 'capsula', 'cosmètic',
                   'corporal', 'capilar', 'essencial', 'esencial'],
    },
    'tomaquet_conserva': {
        'unitat': 'g',
        'inclou': ['tomate triturado', 'tomate pelado', 'tomate frito',
                   'tomàquet triturat', 'tomàquet pelat', 'tomàquet fregit',
                   'passata'],
        'tipus': [],
        'exclou': ['ketchup', 'pizza', 'gazpacho', 'zumo', 'suc ',
                   'crema de tomate', 'crema de tomàquet'],
    },
    'sucre': {
        'unitat': 'g',
        'inclou': ['azúcar ', 'sucre '],
        'tipus': [],
        'exclou': ['edulcorant', 'edulcorante', 'sacarina', 'stevia',
                   'galleta', 'pastís', 'cacau', 'xocolata', 'mermelada'],
    },
    'farina': {
        'unitat': 'g',
        'inclou': ['harina ', 'farina '],
        'tipus': [],
        'exclou': ['tortita', 'buñuelo', 'galleta', 'pastís', 'rebozar',
                   'tempura', 'empanada'],
    },
    'mantequilla': {
        'unitat': 'g',
        'inclou': ['mantequilla ', 'mantega '],
        'tipus': [],
        'exclou': ['cacahuete', 'cacahuet', 'ametlla', 'almendra',
                   'hidratant', 'corporal'],
    },
    'ous': {
        'unitat': 'u',
        'inclou': ['huevos ', 'ous ', 'huevo '],
        'tipus': [],
        'exclou': ['tortilla', 'truita', 'mayonesa', 'maionesa',
                   'rebozado', 'arrebossat', 'plato'],
    },
}

# ── Marques ───────────────────────────────────────────────────────────────────
MARQUES = sorted([
    'central lechera asturiana', 'asturiana', 'pascual', 'puleva omega 3',
    'puleva max', 'puleva', 'kaiku', 'ato', 'letona', 'lauki', 'celta',
    'covap', 'président', 'madriz', 'bonpreu', 'verntallat', 'llet nostra',
    'terra i tast', 'la torre', 'el castillo', 'castillo', 'dia láctea',
    'dia lactea', 'hacendado', 'la cántara', 'ifa', 'carrefour bio',
    'carrefour', 'el buen pastor',
    'danone', 'activia', 'oikos', 'fage', 'vitalinea', 'nestlé', 'chobani',
    'barilla', 'gallo', 'la molisana', 'garofalo',
    'carbonell', 'borges', 'la española', 'hojiblanca',
    'azucarera',
], key=len, reverse=True)

ALIAS_MARCA = {
    'la torre': 'La Torre', 'latorre': 'La Torre',
    'castillo': 'El Castillo', 'el castillo': 'El Castillo',
    'asturiana': 'Central Lechera Asturiana',
    'central lechera asturiana': 'Central Lechera Asturiana',
    'président': 'Président', 'president': 'Président',
    'dia lactea': 'Dia Láctea', 'dia láctea': 'Dia Láctea',
    'puleva omega 3': 'Puleva Omega 3',
    'danone activia': 'Activia', 'activia': 'Activia',
    'danone natural': 'Danone',
}

def extreure_marca(nom):
    nom_lower = nom.lower().strip()
    match = re.match(r'^([A-ZÀÁÈÉÍÏÒÓÚÜÇ][A-ZÀÁÈÉÍÏÒÓÚÜÇ0-9/\s\-\.]+?)\s+[a-z]', nom)
    if match:
        marca_raw = match.group(1).strip()
        nom_net = nom[len(marca_raw):].strip()
        return ALIAS_MARCA.get(marca_raw.lower(), marca_raw.title()), nom_net
    for marca in MARQUES:
        if marca in nom_lower:
            nom_net = re.sub(re.escape(marca), '', nom_lower, flags=re.IGNORECASE).strip()
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            return ALIAS_MARCA.get(marca.lower(), marca.title()), nom_net
    return '', nom.lower()

# ── Traduccions català → castellà ─────────────────────────────────────────────
TRADUCCIONS = sorted({
    'llet': 'leche', 'sencera': 'entera', 'sense lactosa': 'sin lactosa',
    'ecològica': 'ecológica', 'ecològic': 'ecológico', 'calci': 'calcio',
    'iogurt': 'yogur', 'iogur': 'yogur', 'grec': 'griego',
    'desnatat': 'desnatado', 'descremat': 'desnatado',
    'semidesnatat': 'semidesnatado', 'ensucrat': 'azucarado',
    'edulcorat': 'edulcorado', 'cremós': 'cremoso', 'lleuger': 'ligero',
    'per beure': 'para beber',
    'arròs': 'arroz', 'macarrons': 'macarrones', 'fideus': 'fideos',
    'oli': 'aceite', 'verge extra': 'virgen extra', 'gira-sol': 'girasol',
    'sucre': 'azúcar', 'blanc': 'blanco', 'morè': 'moreno',
    'farina': 'harina', 'blat': 'trigo', 'força': 'fuerza',
    'rebosteria': 'repostería', 'mantega': 'mantequilla',
    'ous': 'huevos', 'camperes': 'camperas',
    'maduixa': 'fresa', 'maduixes': 'fresas', 'préssec': 'melocotón',
    'poma': 'manzana', 'plàtan': 'plátano', 'llimona': 'limón',
    'llima': 'lima', 'taronja': 'naranja', 'gerds': 'frambuesas',
    'nabius': 'arándanos', 'prunes': 'ciruelas',
    'fruits silvestres': 'frutos silvestres',
    'fruits del bosc': 'frutos del bosque',
    'fruits vermells': 'frutos rojos',
    'civada': 'avena', 'xia': 'chía', 'nous': 'nueces',
    'ametlles': 'almendras', 'canyella': 'canela',
    'amb': 'con', "d'ovella": 'de oveja',
}.items(), key=lambda x: -len(x[0]))

def normalitzar_nom(nom):
    nom = nom.lower()
    nom = re.sub(r'\(.*?\)', '', nom)
    nom = re.sub(r'\d+\s*u\s*(de\s*)?', '', nom)
    nom = re.sub(r'de\s+\d+\s*(bric|brik|brick)s?\s*(de\s*)?', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\b(brik|bric|brick|botella|ampolla|cartró|cartro|pack|uht)\b', '', nom)
    nom = re.sub(r'\d+[\s,.]?\d*\s*(x\s*)?\d*[\s,.]?\d*\s*(l|ml|kg|g|cl)\b\.?', '', nom)
    nom = re.sub(r'\b(format|viatge|paq\.?|paquet|km0|a2|pasteuritzada|pasteurizada)\b', '', nom)
    nom = re.sub(r'\b(de|con|amb|y)\b\s*$', '', nom)
    nom = re.sub(r'[.,;:()\[\]+]', '', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    for cat, cas in TRADUCCIONS:
        nom = re.sub(r'\b' + re.escape(cat) + r'\b', cas, nom, flags=re.IGNORECASE)
    nom = re.sub(r'\bde nidades\b|\bnidades\b|\bextra\b', '', nom)
    nom = re.sub(r"\bclassic[\'´`]?\b|\bel mercado\b|\bfidias\b|\btarrina\b", '', nom)
    nom = re.sub(r'\bkm0\b|\bartesà\b|\bartesanal\b|\bartesano\b', '', nom)
    nom = re.sub(r'\bsensation\b|\bsin gluten\b|\bestilo\b', '', nom)
    nom = re.sub(r"[\'´`]+", '', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

# ── Parse quantitat ───────────────────────────────────────────────────────────
def parse_quantitat(quantitat, envas, unitat_cat):
    try:
        q_str = str(quantitat).strip()
        envas_str = str(envas).lower().strip()
        if 'kg' in envas_str or re.search(r'\d\s*kg', q_str, re.I):
            unit = 'kg'
        elif 'ml' in envas_str or re.search(r'\d\s*ml', q_str, re.I):
            unit = 'ml'
        elif 'g' in envas_str or re.search(r'\d\s*g\b', q_str, re.I):
            unit = 'g'
        elif 'l' in envas_str or re.search(r'\d\s*l', q_str, re.I):
            unit = 'l'
        elif any(x in envas_str for x in ('u', 'unitat', 'unidad', 'und')):
            unit = 'u'
        else:
            return None
        q_net = re.sub(r'[^\d.,x ]', '', q_str).strip()
        q_net = re.sub(r'\s+', ' ', q_net).strip()
        m = re.match(r'(\d+[.,]?\d*)\s*x\s*(\d+[.,]?\d*)', q_net)
        if m:
            total = float(m.group(1).replace(',', '.')) * float(m.group(2).replace(',', '.'))
        else:
            num = re.match(r'(\d+[.,]?\d*)', q_net)
            if not num:
                return None
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

def arrodonir_mida(val, unitat):
    if val is None: return None
    if unitat == 'l': return round(val, 1)
    if unitat == 'g': return round(val / 25) * 25
    if unitat == 'u': return int(round(val))
    return round(val, 1)

# ── Classificar productes ─────────────────────────────────────────────────────
def classificar(nom_lower):
    for cat_nom, cat in CATEGORIES.items():
        if not any(p in nom_lower for p in cat['inclou']):
            continue
        if cat['tipus'] and not any(t in nom_lower for t in cat['tipus']):
            continue
        if any(e in nom_lower for e in cat['exclou']):
            continue
        return cat_nom
    return None

# ── Processar tots els productes ──────────────────────────────────────────────
print("Classificant productes...")
taula = []
comptador = defaultdict(int)

for f in files:
    nom_orig = str(f.get('producte', ''))
    sup = f.get('supermercat', '')
    try:
        preu = float(str(f.get('preu', '')).replace(',', '.'))
    except Exception:
        continue

    cat = classificar(nom_orig.lower())
    if not cat:
        continue

    unitat = CATEGORIES[cat]['unitat']
    marca, nom_net = extreure_marca(nom_orig)
    nom_norm = normalitzar_nom(nom_net)
    mida = parse_quantitat(f.get('quantitat', ''), f.get('envas', ''), unitat)
    mida_clau = arrodonir_mida(mida, unitat)

    preu_per_u = None
    if preu and mida:
        if unitat == 'g':   preu_per_u = round(preu / mida * 100, 2)
        elif unitat == 'l': preu_per_u = round(preu / mida, 2)
        elif unitat == 'u': preu_per_u = round(preu / mida, 3)

    comptador[cat] += 1
    taula.append({
        'categoria': cat, 'supermercat': sup, 'marca': marca,
        'nom': nom_norm, 'preu': preu, 'mida': mida,
        'mida_clau': mida_clau, 'preu_per_u': preu_per_u, 'unitat': unitat,
    })

print(f"Productes classificats: {len(taula)}")
for cat, n in sorted(comptador.items()):
    print(f"  {cat:<25} {n:>5}")

# ── Agrupar i comparar ────────────────────────────────────────────────────────
print("\nAgrupant i comparant...")
grups = defaultdict(list)
for t in taula:
    if t['mida_clau'] is not None:
        grups[(t['categoria'], t['marca'], t['nom'], t['mida_clau'])].append(t)

files_comp = []
for (cat, marca, nom, mida_clau), entrades in sorted(grups.items()):
    per_sup = defaultdict(list)
    for e in entrades:
        per_sup[e['supermercat']].append(e)
    millors = {s: min(ll, key=lambda x: x['preu']) for s, ll in per_sup.items()}

    if len(millors) < 2:
        continue

    preus = {s: e['preu'] for s, e in millors.items()}
    preu_min  = min(preus.values())
    preu_max  = max(preus.values())
    sup_barat = min(preus, key=preus.get)
    estalvi   = round(preu_max - preu_min, 2)
    estalvi_pct = round((preu_max - preu_min) / preu_max * 100, 1) if preu_max else 0

    unitat = list(millors.values())[0]['unitat']
    if unitat == 'l':   mida_str = f"{mida_clau:.1f}l"
    elif unitat == 'g': mida_str = f"{int(mida_clau)}g"
    else:               mida_str = f"{int(mida_clau)}u"

    fila = [cat, marca or '(marca pròpia)', nom, mida_str]
    for sup in SUPERMERCATS:
        fila.append(millors[sup]['preu'] if sup in millors else '')
    fila += [preu_min, sup_barat, estalvi, f"{estalvi_pct}%", str(date.today())]
    files_comp.append(fila)

print(f"Comparacions trobades (≥2 supermercats): {len(files_comp)}")
cats_count = Counter(f[0] for f in files_comp)
for cat, n in sorted(cats_count.items()):
    print(f"  {cat:<25} {n:>4}")

# ── Guardar a Google Sheets ───────────────────────────────────────────────────
print("\nGuardant a Google Sheets...")
CAPÇALERA = (['Categoria', 'Marca', 'Producte normalitzat', 'Mida'] +
             SUPERMERCATS +
             ['Preu mínim (€)', 'Supermercat més barat', 'Estalvi (€)',
              'Estalvi (%)', 'Data actualització'])

try:
    ws_comp = sheet.worksheet('Comparacions')
    ws_comp.clear()
    print("  Pestanya 'Comparacions' esborrada")
except gspread.WorksheetNotFound:
    ws_comp = sheet.add_worksheet(title='Comparacions', rows=10000, cols=len(CAPÇALERA))
    print("  Pestanya 'Comparacions' creada")

ws_comp.append_row(CAPÇALERA)
if files_comp:
    bloc = 500
    for i in range(0, len(files_comp), bloc):
        ws_comp.append_rows(files_comp[i:i+bloc], value_input_option='USER_ENTERED')
        print(f"  Escrites {min(i+bloc, len(files_comp))}/{len(files_comp)} files...")

print(f"\n✅ Fet! {len(files_comp)} comparacions guardades a 'Comparacions'")
