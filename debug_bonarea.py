# Debug Normalitzador — Iogurts: filtre + comparació de preus
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

# ── Filtre: iogurts ───────────────────────────────────────────────────────────
INCLOU = ['yogur', 'iogurt', 'iogur']

TIPUS_IOGURT = [
    'natural', 'grec', 'griego', 'desnatat', 'desnatado', 'desnat',
    'bífidus', 'bifidus', 'fruita', 'fruta', 'maduixa', 'fresa',
    'plàtan', 'plátano', 'vainilla', 'llimona', 'limón', 'coco',
    'líquid', 'líquido', 'per beure', 'para beber',
    'sense lactosa', 'sin lactosa', 'ecològic', 'ecológico',
    'proteïna', 'proteina', 'skyr',
]

EXCLOU = [
    # brioixeria i galetes
    'bizcocho', 'bescuit', 'bizco', 'tortita', 'coqueta', 'barqueta',
    'galleta', 'barrita', 'cereal', 'muesli', 'sandwich', 'snack',
    # salses i condiments
    'salsa', 'tzatziki',
    # gelats i postres
    'helado', 'gelat', 'polo', 'bombón', 'mousse', 'flan', 'flam',
    'natilla', 'postre', 'pastís', 'pastis', 'pastís', 'lingot',
    # lactis no iogurt
    'queso', 'formatge',
    # begudes
    'batut', 'batido',
    # infantil (purés, bolsites, tarritos)
    'papilla', 'puré', 'bolsita', 'tarrito', 'tarritos', 'danonino',
    'baby', 'bebé', 'nadó', 'nado', '6 meses', '8 meses', '9 meses',
    '12 meses', 'hero baby', 'smileat',
    # cosmètica i neteja
    'corporal', 'facial', 'hidratant', 'hidratante',
    'gel ', 'jabón', 'sabó', 'champú', 'xampú', 'cabell', 'cabello',
    'dosificador', 'dicora',
    # animals
    'gat', 'gos', 'felí', 'canin', 'rosegador', 'vitakraft',
]

productes = []
for f in files:
    nom = str(f.get('producte', '')).lower()
    if any(p in nom for p in INCLOU):
        if not any(e in nom for e in EXCLOU):
            productes.append(f)

print(f"Total iogurts: {len(productes)}\n")

# ── Marques ───────────────────────────────────────────────────────────────────
MARQUES = sorted([
    # marques nacionals
    'danone activia', 'danone natural', 'danone', 'activia',
    'yoplait', 'chobani',
    'pascual', 'kaiku', 'eroski',
    'nestlé griego', 'nestlé',
    'oikos', 'fage',
    'vitalinea', 'sveltesse',
    # marques pròpies
    'hacendado', 'dia láctea', 'dia lactea',
    'bonpreu', 'ifa',
    'carrefour bio', 'carrefour',
    'el castillo', 'castillo',
    'verntallat', 'llet nostra', 'terra i tast',
    # altres
    'alpro', 'silk',
], key=len, reverse=True)

ALIAS_MARCA = {
    'castillo': 'El Castillo',
    'el castillo': 'El Castillo',
    'dia lactea': 'Dia Láctea',
    'dia láctea': 'Dia Láctea',
    'danone activia': 'Activia',
    'activia': 'Activia',
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
    for marca in MARQUES:
        if marca in nom_lower:
            nom_net = re.sub(re.escape(marca), '', nom_lower, flags=re.IGNORECASE).strip()
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            marca_canon = ALIAS_MARCA.get(marca.lower(), marca.title())
            return marca_canon, nom_net
    return '', nom.lower()

TRADUCCIONS = {
    'iogurt': 'yogur',
    'iogur': 'yogur',
    'desnatat': 'desnatado',
    'grec': 'griego',
    'natural': 'natural',
    'sense lactosa': 'sin lactosa',
    'ecològic': 'ecológico',
    'proteïna': 'proteina',
    'fruita': 'fruta',
    'maduixa': 'fresa',
    'plàtan': 'plátano',
    'llimona': 'limón',
    'líquid': 'líquido',
    'per beure': 'para beber',
}

def normalitzar_nom(nom):
    nom = nom.lower()
    nom = re.sub(r'\(.*?\)', '', nom)
    nom = re.sub(r'\d+\s*u\s*(de\s*)?', '', nom)
    nom = re.sub(r'de\s+\d+\s*(u|uni|unitats|unidades)\s*(de\s*)?', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r'\b(pack|format|paq\.?|paquet|envàs|envase)\b', '', nom)
    nom = re.sub(r'\d+[\s,.]?\d*\s*(x\s*)?\d*[\s,.]?\d*\s*(g|kg|ml|l|cl)\b\.?', '', nom)
    nom = re.sub(r'\b(bric|brick|pot|tarro|got|vaso|sobre|bolsa)\b', '', nom)
    nom = re.sub(r'\b(de|con|amb|y|i)\b\s*$', '', nom)
    nom = re.sub(r'[.,;:()\[\]+]', '', nom)
    nom = re.sub(r'\s+', ' ', nom).strip()
    for cat, cas in TRADUCCIONS.items():
        nom = re.sub(r'\b' + re.escape(cat) + r'\b', cas, nom)
    # Treure etiquetes de botiga que contaminen el nom (Carrefour, BonPreu)
    nom = re.sub(r'\bde nidades\b|\bnidades\b', '', nom)
    nom = re.sub(r"\bextra\b|\bclassic[\'´`]?\b|\bel mercado\b", '', nom)
    nom = re.sub(r'\bkm0\b|\bartesà\b|\bartesanal\b|\bartesano\b', '', nom)
    nom = re.sub(r'\bsensation\b|\boikos\b', '', nom)  # sub-marques ja extretes
    nom = re.sub(r'\s+', ' ', nom).strip()
    return nom

# ── Parse pes/volum ───────────────────────────────────────────────────────────
def parse_grams(quantitat, envas):
    """Retorna grams totals del producte. Per iogurts la unitat base és g."""
    try:
        q_str = str(quantitat).strip()
        envas_str = str(envas).lower().strip()

        if 'kg' in envas_str or re.search(r'\d\s*kg', q_str, re.IGNORECASE):
            unit = 'kg'
        elif 'ml' in envas_str or re.search(r'\d\s*ml', q_str, re.IGNORECASE):
            unit = 'ml'  # ml ≈ g per iogurts
        elif 'g' in envas_str or re.search(r'\d\s*g\b', q_str, re.IGNORECASE):
            unit = 'g'
        elif 'l' in envas_str or re.search(r'\d\s*l\b', q_str, re.IGNORECASE):
            unit = 'l'
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

        if unit == 'kg':
            return total * 1000
        elif unit == 'l':
            return total * 1000
        else:
            return total  # g o ml
    except Exception:
        return None

def arrodonir_grams(g):
    if g is None:
        return None
    # Arrodoneix a múltiples de 25g per agrupar presentacions estàndard
    return round(g / 25) * 25

# ── Construir taula normalitzada ──────────────────────────────────────────────
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
    grams = parse_grams(quantitat, envas)
    grams_clau = arrodonir_grams(grams)
    preu_per_100g = round(preu / grams * 100, 2) if (preu and grams) else None
    taula.append({
        'supermercat': sup, 'marca': marca, 'nom': nom_norm,
        'preu': preu, 'quantitat': quantitat, 'envas': envas,
        'grams': grams, 'grams_clau': grams_clau, 'preu_per_100g': preu_per_100g,
    })

# ── Imprimir llista normalitzada ──────────────────────────────────────────────
print("=" * 100)
print(f"{'SUPERMERCAT':<20} {'MARCA':<22} {'NOM NORMALITZAT':<38} {'PREU':>6} {'QUANT':>10}")
print("=" * 100)
for t in taula:
    print(f"{t['supermercat']:<20} {t['marca']:<22} {t['nom']:<38} "
          f"{str(t['preu']):>6}€ {str(t['quantitat'])+' '+str(t['envas']):>10}")

# ── Debug no parsejats ────────────────────────────────────────────────────────
no_parsejats = [t for t in taula if t['grams'] is None]
if no_parsejats:
    print(f"\n⚠️  {len(no_parsejats)} productes sense grams parsejats:")
    for t in no_parsejats:
        print(f"   {t['supermercat']:<20} quant={repr(t['quantitat']):<15} envas={repr(t['envas']):<10} → {t['nom']}")

# ── Mòdul 3: Comparació ───────────────────────────────────────────────────────
grups = defaultdict(list)
for t in taula:
    if t['grams_clau'] is not None:
        grups[(t['marca'], t['nom'], t['grams_clau'])].append(t)

print(f"\n\n{'='*90}")
print("MÒDUL 3 — COMPARACIÓ IOGURTS (mateixa marca + tipus + pes)")
print(f"{'='*90}")

grups_multi = 0
for (marca, nom, grams), entrades in sorted(grups.items()):
    per_sup = defaultdict(list)
    for e in entrades:
        per_sup[e['supermercat']].append(e)
    per_sup_unic = {sup: min(ll, key=lambda x: x['preu']) for sup, ll in per_sup.items()}
    if len(per_sup_unic) < 2:
        continue
    grups_multi += 1
    etiqueta = f"{marca} — {nom}" if marca else f"(sense marca) — {nom}"
    mida = f"{int(grams)}g" if grams == int(grams) else f"{grams}g"
    print(f"\n  {'─'*86}")
    print(f"  {etiqueta}  [{mida}]")
    entrades_ord = sorted(per_sup_unic.values(), key=lambda x: x['preu'])
    min_preu = entrades_ord[0]['preu']
    for e in entrades_ord:
        diferencia = f"  (+{e['preu']-min_preu:.2f}€)" if e['preu'] > min_preu else ''
        estrella = '★' if e['preu'] == min_preu else ' '
        p100 = f"  ({e['preu_per_100g']:.2f}€/100g)" if e['preu_per_100g'] else ''
        print(f"  {estrella} {e['supermercat']:<22} {e['preu']:.2f}€{p100}{diferencia}")

print(f"\n{'='*90}")
print(f"Total grups únics (marca+tipus+pes): {len(grups)}")
print(f"Grups presents a ≥2 supermercats: {grups_multi}")
