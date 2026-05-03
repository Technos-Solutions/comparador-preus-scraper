# Debug Normalitzador — Mòdul 3: comparació de preus per litre
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json, os, re
from collections import defaultdict

creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds_dict = json.loads(creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Comparador_Preus_DB')
ws = sheet.worksheet('Preus')

print("✅ Connectat a Google Sheets")
files = ws.get_all_records()

# ── Filtre: llet per beure ────────────────────────────────────────────────────
INCLOU = ['leche ', 'llet ']
TIPUS_LLET = ['entera', 'sencera', 'desnat', 'semidenat', 'semidesnat',
              'fresca', 'sense lactosa', 'sin lactosa', 'calcio', 'calci',
              'omega 3', 'ecològica', 'ecológica', 'barista', 'proteina', 'proteïna']
EXCLOU = [
    'yogur', 'iogurt', 'bífidus', 'bifidus', 'queso', 'formatge',
    'bebida', 'condensada', 'polvo', 'pols', 'fermentada', 'kéfir', 'quefir',
    'chocolate', 'xocolata', 'café', 'cafè', 'cacao', 'cacau',
    'galleta', 'barrita', 'cereal', 'arroz', 'arròs', 'natilla',
    'helado', 'gelat', 'mousse', 'flan', 'flam', 'dulce de leche', 'dolç de llet',
    'bollería', 'bizcocho', 'pan ', 'pa ', 'pastel', 'brownie',
    'frita', 'frito', 'panes', 'bollito', 'phoskito', 'salchicha', 'campof',
    'solar', 'corporal', 'facial', 'limpiadora', 'netejadora', 'aftersun',
    'fps', 'spf', 'fp-', 'protector', 'protectora', 'hidratant', 'hidratante',
    'gel ', 'jabón', 'sabó', 'dentífric', 'champú', 'xampú', 'paper ',
    'scottex', 'desenredant', 'reafirmant', 'delial', 'denenes', 'nivea', 'ecran',
    'bronceja', 'bronzeja',
    'gat', 'gos', 'felí', 'canin', 'felix ', 'youwup', 'yowup',
    'ametll', 'coco', 'avena', 'civada', 'soja', 'vegetal',
    'suc amb llet', 'suc de fruites', 'zumo', 'fruta ', 'fruita ',
    'nata', 'evaporada', 'crema ', 'rotllet', 'farcellet',
    'puré', 'batut', 'batido',
    'infantil', 'lactant', 'creixement', 'crecimiento', 'materna',
    'almirón', 'nativa', 'nestlé junior', 'blemil', 'nidina', 'blédina',
    'llibre', 'barcanova', 'bullet ', 'vi rosat',
    'càpsula', 'cápsula', 'dolce gusto', 'folic', 'nous',
]

productes = []
for f in files:
    nom = str(f.get('producte', '')).lower()
    if any(p in nom for p in INCLOU):
        if any(t in nom for t in TIPUS_LLET):
            if not any(e in nom for e in EXCLOU):
                productes.append(f)

print(f"Total llets per beure: {len(productes)}\n")

# ── Marques ───────────────────────────────────────────────────────────────────
MARQUES = sorted([
    'central lechera asturiana', 'asturiana',
    'pascual calci', 'pascual',
    'puleva omega3', 'puleva omega 3', 'puleva max', 'puleva',
    'kaiku s/lactosa', 'kaiku',
    'ato natura', 'ato',
    'letona', 'lauki', 'celta', 'covap',
    'president', 'président',
    'rio', 'río', 'madriz',
    'bonpreu', 'verntallat', 'llet nostra', 'terra i tast',
    'latorre', 'la torre', 'el castillo', 'castillo',
    'dia láctea', 'dia lactea', 'hacendado',
    'gaza', 'la cántara',
    'ifa', 'carrefour bio', 'carrefour', 'el buen pastor',
], key=len, reverse=True)

ALIAS_MARCA = {
    'latorre': 'La Torre',
    'la torre': 'La Torre',
    'castillo': 'El Castillo',
    'el castillo': 'El Castillo',
    'asturiana': 'Central Lechera Asturiana',
    'central lechera asturiana': 'Central Lechera Asturiana',
    'president': 'Président',
    'président': 'Président',
    'dia lactea': 'Dia Láctea',
    'dia láctea': 'Dia Láctea',
    'puleva omega3': 'Puleva Omega 3',
    'puleva omega 3': 'Puleva Omega 3',
}

def extreure_marca(nom):
    nom_lower = nom.lower().strip()
    # BonPreu: prefix en MAJÚSCULES
    match = re.match(r'^([A-ZÀÁÈÉÍÏÒÓÚÜÇ][A-ZÀÁÈÉÍÏÒÓÚÜÇ0-9/\s\-\.]+?)\s+[a-z]', nom)
    if match:
        marca_raw = match.group(1).strip()
        nom_net = nom[len(marca_raw):].strip()
        marca_canon = ALIAS_MARCA.get(marca_raw.lower(), marca_raw.title())
        return marca_canon, nom_net
    # Resta: buscar marca coneguda
    for marca in MARQUES:
        if marca in nom_lower:
            nom_net = re.sub(re.escape(marca), '', nom_lower, flags=re.IGNORECASE).strip()
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            marca_canon = ALIAS_MARCA.get(marca.lower(), marca.title())
            return marca_canon, nom_net
    return '', nom.lower()

TRADUCCIONS = {
    'llet': 'leche', 'sencera': 'entera', 'desnatada': 'desnatada',
    'semidesnatada': 'semidesnatada', 'sense lactosa': 'sin lactosa',
    'ecològica': 'ecológica', 'proteïna': 'proteina',
    'calci': 'calcio', 'fresca': 'fresca', 'barista': 'barista',
}

def normalitzar_nom(nom):
    nom = nom.lower()
    nom = re.sub(r'\(.*?\)', '', nom)
    nom = re.sub(r'\d+\s*u\s*(de\s*)?', '', nom)
    nom = re.sub(r'de\s+\d+\s*(bric|brik|brick)s?\s*(de\s*)?', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\b(brik|bric|brick|botella|ampolla|cartró|cartro|pack|en cartró|en ampolla|uht)\b', '', nom)
    nom = re.sub(r'\d+[\s,.]?\d*\s*(x\s*)?\d*[\s,.]?\d*\s*(l|ml|kg|g|cl)\b\.?', '', nom)
    nom = re.sub(r'\b(format|viatge|paq\.?|paquet|km0|km|a2|pasteuritzada|pasteurizada|pasteurisée)\b', '', nom)
    nom = re.sub(r'\b(de|con)\b\s*$', '', nom)
    nom = re.sub(r'[.,;:()\[\]+]', '', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    for cat, cas in TRADUCCIONS.items():
        nom = re.sub(r'\b' + re.escape(cat) + r'\b', cas, nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    # Ordre estàndard: leche [tipus] [qualitat]
    nom = re.sub(r'^(leche)\s+(sin lactosa|con calcio|fresca|ecológica)\s+(entera|semidesnatada|desnatada)',
                 r'\1 \3 \2', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

# ── Mòdul 3: Preu per litre i comparació ─────────────────────────────────────
def parse_litres(quantitat, envas):
    """Converteix quantitat + envas a litres totals. Accepta unitats dins del camp quantitat."""
    try:
        q_str = str(quantitat).strip()
        envas_str = str(envas).lower().strip()

        # Detectar unitat: primer al camp envas, després dins quantitat
        if 'ml' in envas_str:
            unit = 'ml'
        elif envas_str in ('l', 'botella', 'brik', 'ampolla', 'pack-6', 'pack', 'pack6'):
            unit = 'l'
        elif re.search(r'\d\s*ml', q_str, re.IGNORECASE):
            unit = 'ml'
        elif re.search(r'\d\s*l', q_str, re.IGNORECASE):
            # "6 x 1L", "1.5L", "0.2L", "1 l", etc.
            unit = 'l'
        else:
            return None

        # Netejar q_str: treure lletres i signes excepte dígits, coma, punt, x, espai
        q_net = re.sub(r'[^\d.,x ]', '', q_str, flags=re.IGNORECASE).strip()
        q_net = re.sub(r'\s+', ' ', q_net).strip()

        # Format "N x M" → N * M
        m = re.match(r'(\d+[.,]?\d*)\s*x\s*(\d+[.,]?\d*)', q_net)
        if m:
            total = float(m.group(1).replace(',', '.')) * float(m.group(2).replace(',', '.'))
        else:
            num = re.match(r'(\d+[.,]?\d*)', q_net)
            if not num:
                return None
            total = float(num.group(1).replace(',', '.'))

        return total / 1000 if unit == 'ml' else total
    except Exception:
        return None

# Construïm la taula normalitzada
taula = []
for p in productes:
    nom_original = p.get('producte', '')
    sup = p.get('supermercat', '')
    try:
        preu = float(str(p.get('preu', '')).replace(',', '.'))
    except Exception:
        preu = None
    quantitat = p.get('quantitat', '')
    envas = p.get('envas', '')
    marca, nom_net = extreure_marca(nom_original)
    nom_norm = normalitzar_nom(nom_net)
    litres = parse_litres(quantitat, envas)
    preu_per_l = round(preu / litres, 2) if (preu and litres) else None
    taula.append({
        'supermercat': sup, 'marca': marca, 'nom': nom_norm,
        'preu': preu, 'quantitat': quantitat, 'envas': envas,
        'litres': litres, 'preu_per_l': preu_per_l,
    })

# ── Debug parse litres ────────────────────────────────────────────────────────
no_parsejats = [t for t in taula if t['litres'] is None]
if no_parsejats:
    print(f"⚠️  {len(no_parsejats)} productes sense litres parsejats:")
    for t in no_parsejats:
        print(f"   {t['supermercat']:<20} quant={repr(t['quantitat']):<15} envas={repr(t['envas']):<15} → {t['nom']}")
print()

# Agrupar per (marca, nom, litres_arrodonits) — mateixa presentació
def arrodonir_litres(l):
    """Arrodoneix a 1 decimal per agrupar presentacions estàndard."""
    if l is None:
        return None
    return round(l, 1)

grups = defaultdict(list)
for t in taula:
    litres_clau = arrodonir_litres(t['litres'])
    if litres_clau is not None:
        grups[(t['marca'], t['nom'], litres_clau)].append(t)

# ── Mostrar comparació: grups presents a ≥2 supermercats ─────────────────────
print("\n" + "=" * 90)
print("MÒDUL 3 — COMPARACIÓ DE PREUS (mateixa marca + tipus + presentació)")
print("=" * 90)

grups_multi = 0
for (marca, nom, litres), entrades in sorted(grups.items()):
    # Un producte per supermercat (si n'hi ha més d'un, agafem el més barat)
    per_sup = defaultdict(list)
    for e in entrades:
        per_sup[e['supermercat']].append(e)
    per_sup_unic = {sup: min(llista, key=lambda x: x['preu']) for sup, llista in per_sup.items()}

    if len(per_sup_unic) < 2:
        continue
    grups_multi += 1

    etiqueta = f"{marca} — {nom}" if marca else f"(sense marca) — {nom}"
    mida = f"{litres:.1f}l"
    print(f"\n  {'─'*86}")
    print(f"  {etiqueta}  [{mida}]")

    entrades_ord = sorted(per_sup_unic.values(), key=lambda x: x['preu'])
    min_preu = entrades_ord[0]['preu']
    for e in entrades_ord:
        diferencia = f"  (+{e['preu']-min_preu:.2f}€)" if e['preu'] > min_preu else ''
        estrella = '★' if e['preu'] == min_preu else ' '
        ppl = f"  ({e['preu_per_l']:.2f}€/l)" if e['preu_per_l'] else ''
        print(f"  {estrella} {e['supermercat']:<22} {e['preu']:.2f}€{ppl}{diferencia}")

print(f"\n{'='*90}")
print(f"Total grups únics (marca+tipus+mida): {len(grups)}")
print(f"Grups presents a ≥2 supermercats: {grups_multi}")
