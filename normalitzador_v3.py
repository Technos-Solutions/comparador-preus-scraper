# normalitzador_v3.py — Compara el mateix producte entre supermercats com ho faria una persona
#
# Diferencia amb el v2: el v2 demanava a Gemini un nom lliure en catala i comparava text
# exacte, i el mateix producte acabava amb noms diferents ("refresc cola", "refresc de cua"...).
# El v3 demana ATRIBUTS (marca, producte, variant, marca blanca, format) i la comparacio la fa
# el codi. Validat als diagnostics del 28/09 i l'01/10 (debug_mateix_producte.py,
# debug_normalitzador_v3.py). Veure INCIDENCIES.md, apartat "Normalitzador v3".
#
# Flux:
#   Pas A (categoria): es reaprofita la categoria de la cache del v2 (Productes_Normalitzats);
#     nomes es demana a Gemini per als productes que no hi son.
#   Pas B (atributs): nomes productes nous (no a Productes_Atributs), per categoria, en lots que
#     barregen supermercats. Cada lot rep el VOCABULARI de la categoria (noms de producte,
#     variants i marques ja fets servir) i l'ha de reutilitzar: aixi el nom no depen de la crida.
#     La cache es desa despres de CADA lot (si el run s'atura, no es perd res).
#   Comparacio (codi, sense Gemini) -> pestanya Comparacions_v3:
#     - Marca comercial: mateixa marca + producte + variant, a 2 o mes supermercats
#     - Marca blanca: mateix producte + variant entre la marca propia de cada supermercat
#       (llista de Marques_Blanques + criteri de Gemini + productes sense marca)
#     - Nomes es comparen unitats iguals (€/l, €/kg o €/u)
#
# Pestanyes que escriu (no toca Preus, Productes_Normalitzats ni Comparacions_v2):
#   Productes_Atributs  cache d'atributs (una fila per supermercat + nom)
#   Marques_Blanques    marca, supermercat, estat (confirmada / pendent / descartada).
#                       Gemini hi afegeix candidates com a "pendent"; el David les revisa.
#                       Les "descartada" no compten mai com a marca blanca.
#   Comparacions_v3     resultat
#
# Variables d'entorn opcionals (per fer la primera passada per parts):
#   MAX_PRODUCTES  maxim de productes nous a enviar a Gemini en aquest run (0 = sense limit)
#   CATEGORIES     llista separada per comes; si es posa, nomes es processen aquestes categories
#   NOMES_COMPARAR "1" per no cridar Gemini i nomes recalcular Comparacions_v3

import json
import os
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import date

MODEL = 'gemini-3.5-flash'
MIDA_LOT = 80                 # productes per crida al pas B
MIDA_LOT_CATEGORIA = 150      # productes per crida al pas A
TEMPS_MAXIM = 300 * 60        # el workflow te timeout de 330 min: s'atura net abans
LLINDAR_LOTS_FALLITS = 5

SUPERMERCATS = ['Mercadona', 'Bon Àrea', 'Dia', 'Bon Preu / Esclat', 'Carrefour']

CATEGORIES = [
    'iogurt', 'llet', 'beguda_vegetal', 'formatge', 'embotit', 'carn', 'peix', 'marisc',
    'ous', 'mantequilla', 'pasta', 'arros', 'llegum', 'cereals', 'farina', 'sucre', 'oli',
    'vinagre', 'tomaquet_conserva', 'conserva', 'sopa', 'condiment', 'salsa', 'melmelada',
    'mel', 'pa', 'brioixeria', 'galeta', 'xocolata', 'snack', 'fruit_sec', 'congelat',
    'verdura', 'fruita', 'cafe', 'te', 'aigua', 'refresc', 'suc', 'cervesa', 'vi', 'licor',
    'neteja_llar', 'higiene_personal', 'cura_personal', 'bolquer', 'mascota',
    'parafarmacia', 'altra',
]

# Llavor de la pestanya Marques_Blanques (nomes s'usa si la pestanya no existeix).
# Les que comencen igual que el supermercat (Dia Láctea, Carrefour Bio...) es detecten per prefix.
MARQUES_BLANQUES_INICIALS = {
    'Mercadona': ['Hacendado', 'Deliplus', 'Bosque Verde', 'Compy', 'Casa Juncal'],
    'Dia': ['Dia', 'Vegecampo', 'Delicious Dia', 'Bonté', 'La Almazara del Olivar',
            'El Molino de Dia'],
    'Carrefour': ['Carrefour', 'El Mercado', 'De Nuestra Tierra', 'Simpl', 'Sensation'],
    'Bon Preu / Esclat': ['Bonpreu', 'Esclat', 'Ifa', 'La Collita'],
    'Bon Àrea': ['bonÀrea', 'Bon Àrea'],
}

CAPCALERA_ATRIBUTS = ['supermercat', 'nom_original', 'categoria', 'marca', 'producte', 'variant',
                      'marca_blanca', 'unitats', 'mida', 'unitat', 'data']
CAPCALERA_MARQUES = ['marca', 'supermercat', 'estat', 'origen', 'data']
CAPCALERA_COMPARACIONS = (
    ['Tipus', 'Categoria', 'Marca', 'Producte', 'Variant', 'Unitat'] + SUPERMERCATS +
    ['Preu mínim', 'Supermercat més barat', 'Estalvi', 'Estalvi (%)', 'Producte més barat',
     'Data actualització'])

PROMPT_CATEGORIA = """Classifica cada producte de supermercat en UNA d'aquestes categories:
""" + ' · '.join(CATEGORIES) + """
Fes servir "altra" només si de veritat no encaixa en cap altra.
Entrada: llista JSON [{"id", "n" (nom)}]. Retorna NOMÉS JSON compacte:
{"r": [[id, categoria], ...]}"""

PROMPT_ATRIBUTS = """Ets una persona que compara preus entre supermercats (Mercadona, Bon Àrea,
Dia, Bon Preu/Esclat i Carrefour). Reps productes d'una mateixa categoria. Cada
supermercat escriu el nom a la seva manera (català o castellà).

Reps també un VOCABULARI amb els noms que ja s'han fet servir en aquesta categoria.
REGLA PRINCIPAL: si un producte és el mateix que un del vocabulari, fes servir
EXACTAMENT el mateix text de "producte", les mateixes variants i la mateixa marca.
Crea un nom nou només si no n'hi ha cap d'equivalent.

Per a cada producte, extreu:
- marca: marca comercial, sempre escrita igual (p. ex. "Coca-Cola", "Hacendado").
  Si no n'hi ha, "".
- producte: què és, en català, genèric i curt ("llet", "oli d'oliva", "refresc de cola").
- variant: llista de trets que fan que, per a qui compra, sigui un producte DIFERENT
  (["sencera"], ["sencera", "sense lactosa"], ["zero sucre"], ["verge extra"],
  ["amb gas"]...), en català i minúscules. NO hi posis trets de procés o de
  màrqueting que no canvien el producte ("pasteuritzada", "original", "clàssic",
  "de sempre"), ni format, envàs o quantitat. [] si és la versió normal.
- marca_blanca: 1 si és la marca pròpia del supermercat on es ven (Hacendado de
  Mercadona, Dia Láctea de Dia, Carrefour/El Mercado de Carrefour, Bonpreu/Ifa de
  Bon Preu, Bon Àrea...), 0 si no.
- unitats, mida, unitat: format del pack. unitat és "ml", "g" o "u". Converteix
  l i cl a ml, kg a g. Fes servir el nom i "q" (la quantitat de la web): si el nom
  no diu la mida, fes servir q; si q és la mida d'una sola unitat però el nom diu
  que és un pack ("pack 6 botellas 1 l"), és 6 x 1000 ml. Sense dades, mida 0.

Entrada: {"vocabulari": {...}, "productes": [{"id", "s" (supermercat), "n" (nom), "q"}]}
Retorna NOMÉS JSON compacte, una fila per producte i en el mateix ordre:
{"r": [[id, marca, producte, [variants], marca_blanca, unitats, mida, unitat], ...]}
"""

# Senyals d'error del compte de Gemini: no te sentit continuar
SENYALS_ERROR_COMPTE = (
    'prepayment', 'credits are depleted', 'billing', 'spending cap', 'spend cap',
    'api key not valid', 'api_key_invalid', 'permission denied', 'permission_denied',
)


class AturadaGemini(Exception):
    """El compte o la quota de Gemini no permeten continuar: es desa el que hi ha i s'atura."""


# ── Utilitats ─────────────────────────────────────────────────────────────────
def sense_accents(text):
    text = unicodedata.normalize('NFKD', str(text or '')).encode('ascii', 'ignore').decode()
    return ' '.join(text.lower().replace('-', ' ').split())


def a_float(valor):
    try:
        return float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        return 0.0


def numero_net(valor):
    return int(valor) if float(valor).is_integer() else round(valor, 3)


def text_variant(variants):
    return ', '.join(sorted({str(v).strip().lower() for v in (variants or []) if str(v).strip()}))


def preu_unitat(preu, unitats, mida, unitat):
    total = a_float(unitats or 1) * a_float(mida)
    if preu <= 0 or total <= 0:
        return None, ''
    if unitat == 'ml':
        return preu / total * 1000, '€/l'
    if unitat == 'g':
        return preu / total * 1000, '€/kg'
    if unitat == 'u':
        return preu / total, '€/u'
    return None, ''


def ordre_barrejat(productes):
    # Alterna supermercats: cada lot en te de tots i el vocabulari es posa a prova entre lots
    per_super = defaultdict(list)
    for p in productes:
        per_super[p['supermercat']].append(p)
    ordre = SUPERMERCATS + sorted(s for s in per_super if s not in SUPERMERCATS)
    resultat = []
    while any(per_super.values()):
        for s in ordre:
            if per_super.get(s):
                resultat.append(per_super[s].pop(0))
    return resultat


# ── Marques blanques ──────────────────────────────────────────────────────────
class MarquesBlanques:
    def __init__(self, files):
        # files: dicts amb marca, supermercat, estat
        self.estat = {}   # (supermercat, marca normalitzada) -> estat
        for f in files:
            clau = (str(f.get('supermercat', '')).strip(), sense_accents(f.get('marca')))
            if clau[1]:
                self.estat[clau] = str(f.get('estat', '')).strip().lower() or 'confirmada'
        self.noves = []   # candidates detectades en aquest run: [marca, supermercat]

    def _estat(self, marca, supermercat):
        m = sense_accents(marca)
        for (s, b), estat in self.estat.items():
            if s == supermercat and (m == b or m.startswith(b + ' ')):
                return estat
        return None

    def es_blanca(self, marca, supermercat, segons_gemini):
        if not sense_accents(marca):
            return True   # sense marca: producte propi o generic del supermercat
        estat = self._estat(marca, supermercat)
        if estat == 'descartada':
            return False
        if estat in ('confirmada', 'pendent'):
            return True
        return bool(segons_gemini)

    def apuntar_candidata(self, marca, supermercat, segons_gemini):
        if segons_gemini and sense_accents(marca) and self._estat(marca, supermercat) is None:
            self.estat[(supermercat, sense_accents(marca))] = 'pendent'
            self.noves.append([marca, supermercat])


# ── Vocabulari per categoria ──────────────────────────────────────────────────
def construir_vocabularis(atributs):
    vocabularis = defaultdict(lambda: {'productes': defaultdict(Counter), 'marques': Counter()})
    for a in atributs.values():
        v = vocabularis[a['categoria']]
        if a['producte']:
            v['productes'][a['producte']][a['variant']] += 1
        if a['marca']:
            v['marques'][a['marca']] += 1
    return vocabularis


def vocabulari_per_prompt(v, max_productes=400, max_variants=20, max_marques=200):
    # Els productes, variants i marques mes frequents primer; es limita per no inflar el
    # prompt a les categories grans (p. ex. "altra")
    frequents = sorted(v['productes'].items(), key=lambda kv: -sum(kv[1].values()))[:max_productes]
    return {
        'productes': {p: [var for var, _ in c.most_common(max_variants)]
                      for p, c in sorted(frequents)},
        'marques': [m for m, _ in v['marques'].most_common(max_marques)],
    }


# ── Gemini ────────────────────────────────────────────────────────────────────
class ClientGemini:
    def __init__(self, api_key):
        from google import genai
        from google.genai import types
        self.client = genai.Client(api_key=api_key)
        self.config = types.GenerateContentConfig(
            response_mime_type='application/json', temperature=0.0,
            thinking_config=types.ThinkingConfig(thinking_budget=0))
        self.tokens_entrada = 0
        self.tokens_sortida = 0

    def cridar(self, prompt, dades, reintents=3):
        contingut = prompt + "\n\n" + json.dumps(dades, ensure_ascii=False)
        for intent in range(reintents):
            try:
                resp = self.client.models.generate_content(
                    model=MODEL, contents=contingut, config=self.config)
                us = resp.usage_metadata
                self.tokens_entrada += us.prompt_token_count or 0
                self.tokens_sortida += (us.candidates_token_count or 0) + (us.thoughts_token_count or 0)
                return json.loads(resp.text).get('r', [])
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON invalid de Gemini: {e}")
                return []
            except Exception as e:
                missatge = str(e)
                if any(s in missatge.lower() for s in SENYALS_ERROR_COMPTE):
                    raise AturadaGemini(f"Error del compte de Gemini: {missatge[:300]}")
                if 'per day' in missatge.lower() or 'daily' in missatge.lower():
                    raise AturadaGemini(f"Quota diaria de Gemini esgotada: {missatge[:300]}")
                if '429' in missatge or 'RESOURCE_EXHAUSTED' in missatge:
                    espera = 60 * (intent + 1)
                    print(f"   ⏳ Rate limit ({missatge[:150]}): esperant {espera}s")
                    time.sleep(espera)
                    continue
                print(f"   ❌ Error Gemini: {missatge[:300]}")
                return []
        return []


def demanar_categories(gemini, productes):
    resultat = {}
    for i in range(0, len(productes), MIDA_LOT_CATEGORIA):
        lot = productes[i:i + MIDA_LOT_CATEGORIA]
        files = gemini.cridar(PROMPT_CATEGORIA, [{'id': p['id'], 'n': p['producte']} for p in lot])
        for f in files:
            if isinstance(f, list) and len(f) >= 2:
                resultat[str(f[0])] = f[1] if f[1] in CATEGORIES else 'altra'
        print(f"   Pas A: {min(i + MIDA_LOT_CATEGORIA, len(productes))}/{len(productes)} classificats")
    return resultat


def demanar_atributs(gemini, vocabulari, lot):
    dades = {'vocabulari': vocabulari_per_prompt(vocabulari),
             'productes': [{'id': p['id'], 's': p['supermercat'], 'n': p['producte'],
                            'q': p['quantitat']} for p in lot]}
    resultat = {}
    for f in gemini.cridar(PROMPT_ATRIBUTS, dades):
        if not (isinstance(f, list) and len(f) >= 8):
            continue
        _, marca, producte, variants, mb, unitats, mida, unitat = f[:8]
        unitat = str(unitat or '').strip().lower()
        resultat[str(f[0])] = {
            'marca': str(marca or '').strip(),
            'producte': str(producte or '').strip().lower(),
            'variant': text_variant(variants if isinstance(variants, list) else [variants]),
            'marca_blanca': 1 if str(mb).strip() in ('1', 'True', 'true') else 0,
            'unitats': numero_net(a_float(unitats) or 1),
            'mida': numero_net(a_float(mida)),
            'unitat': unitat if unitat in ('ml', 'g', 'u') else '',
        }
    return resultat


# ── Comparacio (sense Gemini) ─────────────────────────────────────────────────
def comparar(preus, atributs, marques):
    comercials, blanques = defaultdict(list), defaultdict(list)
    for f in preus:
        clau = (f['supermercat'], f['producte'])
        a = atributs.get(clau)
        if not a or not a['producte']:
            continue
        pu, u = preu_unitat(f['preu'], a['unitats'], a['mida'], a['unitat'])
        if not pu:
            continue
        entrada = dict(f, pu=pu, u=u, marca=a['marca'])
        if marques.es_blanca(a['marca'], f['supermercat'], a['marca_blanca']):
            blanques[(a['categoria'], a['producte'], a['variant'], u)].append(entrada)
        else:
            comercials[(a['categoria'], sense_accents(a['marca']), a['producte'], a['variant'], u)].append(entrada)

    files = []
    for tipus, grups in (('Marca comercial', comercials), ('Marca blanca', blanques)):
        for clau, entrades in grups.items():
            millors = {}
            for e in entrades:
                if e['supermercat'] not in millors or e['pu'] < millors[e['supermercat']]['pu']:
                    millors[e['supermercat']] = e
            if len(millors) < 2:
                continue
            categoria, producte, variant, u = clau[0], clau[-3], clau[-2], clau[-1]
            if tipus == 'Marca comercial':
                marca = Counter(e['marca'] for e in entrades).most_common(1)[0][0]
            else:
                marca = ' / '.join(sorted({e['marca'] or '(sense marca)' for e in millors.values()}))
            min_pu = min(e['pu'] for e in millors.values())
            max_pu = max(e['pu'] for e in millors.values())
            barat = min(millors.values(), key=lambda e: e['pu'])
            fila = [tipus, categoria, marca, producte, variant or 'normal', u]
            fila += [round(millors[s]['pu'], 3) if s in millors else '' for s in SUPERMERCATS]
            fila += [round(min_pu, 3), barat['supermercat'], round(max_pu - min_pu, 3),
                     f"{round((max_pu - min_pu) / max_pu * 100, 1) if max_pu else 0}%",
                     barat['producte'], str(date.today())]
            files.append(fila)
    files.sort(key=lambda f: (f[1], f[0], f[3], f[4], f[2]))
    return files


# ── Google Sheets ─────────────────────────────────────────────────────────────
def obrir_o_crear(sheet, titol, capcalera, files=50000, files_inicials=None):
    import gspread
    try:
        return sheet.worksheet(titol), False
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=titol, rows=files, cols=len(capcalera))
        ws.append_row(capcalera)
        if files_inicials:
            ws.append_rows(files_inicials, value_input_option='RAW')
        print(f"   Pestanya '{titol}' creada")
        return ws, True


def llegir_preus(sheet):
    preus = []
    for f in sheet.worksheet('Preus').get_all_records():
        nom = str(f.get('producte', '')).strip()
        if nom:
            preus.append({'supermercat': str(f.get('supermercat', '')).strip(), 'producte': nom,
                          'preu': a_float(f.get('preu')), 'quantitat': str(f.get('quantitat', '') or '')})
    return preus


def llegir_atributs(ws):
    atributs = {}
    for f in ws.get_all_records():
        clau = (str(f.get('supermercat', '')).strip(), str(f.get('nom_original', '')).strip())
        if clau[1]:
            atributs[clau] = {
                'categoria': str(f.get('categoria', '')).strip(), 'marca': str(f.get('marca', '')).strip(),
                'producte': str(f.get('producte', '')).strip(), 'variant': str(f.get('variant', '')).strip(),
                'marca_blanca': a_float(f.get('marca_blanca')), 'unitats': a_float(f.get('unitats')) or 1,
                'mida': a_float(f.get('mida')), 'unitat': str(f.get('unitat', '')).strip()}
    return atributs


def desar_comparacions(sheet, files):
    import gspread
    try:
        ws = sheet.worksheet('Comparacions_v3')
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title='Comparacions_v3', rows=max(1000, len(files) + 10),
                                 cols=len(CAPCALERA_COMPARACIONS))
    ws.append_row(CAPCALERA_COMPARACIONS)
    for i in range(0, len(files), 500):
        ws.append_rows(files[i:i + 500], value_input_option='USER_ENTERED')


# ── Programa principal ────────────────────────────────────────────────────────
def main():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    inici = time.time()
    max_productes = int(os.environ.get('MAX_PRODUCTES', '0') or 0)
    filtre_categories = [c.strip() for c in os.environ.get('CATEGORIES', '').split(',') if c.strip()]
    nomes_comparar = os.environ.get('NOMES_COMPARAR', '') == '1'

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CREDENTIALS']),
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive'])
    sheet = gspread.authorize(creds).open('Comparador_Preus_DB')
    print("✅ Connectat a Google Sheets")

    preus = llegir_preus(sheet)
    print(f"Preus: {len(preus)} productes {dict(Counter(p['supermercat'] for p in preus))}")
    cache_v2 = {str(r['nom_original']).strip(): str(r.get('categoria', '')).strip()
                for r in sheet.worksheet('Productes_Normalitzats').get_all_records()
                if str(r.get('nom_original', '')).strip()}
    ws_atributs, _ = obrir_o_crear(sheet, 'Productes_Atributs', CAPCALERA_ATRIBUTS)
    atributs = llegir_atributs(ws_atributs)
    llavor = [[m, s, 'confirmada', 'llista inicial', str(date.today())]
              for s, ll in MARQUES_BLANQUES_INICIALS.items() for m in ll]
    ws_marques, _ = obrir_o_crear(sheet, 'Marques_Blanques', CAPCALERA_MARQUES, 2000, llavor)
    marques = MarquesBlanques(ws_marques.get_all_records())
    print(f"Cache v2: {len(cache_v2)} | atributs v3: {len(atributs)} | marques blanques: {len(marques.estat)}")

    # Productes nous: els que no tenen atributs (un sol cop per supermercat + nom)
    nous, vistos = [], set()
    for p in preus:
        clau = (p['supermercat'], p['producte'])
        if clau not in atributs and clau not in vistos:
            vistos.add(clau)
            nous.append(dict(p, id=f"P{len(nous)}", categoria=cache_v2.get(p['producte'], '')))
    print(f"Productes nous sense atributs: {len(nous)}")

    if nous and not nomes_comparar:
        gemini = ClientGemini(os.environ['GEMINI_API_KEY'])
        motiu_aturada = None
        try:
            # Pas A: categoria per als que no en tenen (o en tenen una que ja no existeix)
            sense_categoria = [p for p in nous if p['categoria'] not in CATEGORIES]
            if filtre_categories:
                sense_categoria = []   # en runs per categoria, nomes es tracten les conegudes
            if sense_categoria:
                print(f"\nPas A: {len(sense_categoria)} productes sense categoria")
                categories = demanar_categories(gemini, sense_categoria)
                for p in sense_categoria:
                    p['categoria'] = categories.get(p['id'], '')

            pendents = [p for p in nous if p['categoria'] in CATEGORIES]
            if filtre_categories:
                pendents = [p for p in pendents if p['categoria'] in filtre_categories]
            per_categoria = defaultdict(list)
            for p in pendents:
                per_categoria[p['categoria']].append(p)
            # Primer les categories mes petites: si cal tallar per MAX_PRODUCTES, se'n completen mes
            ordre = sorted(per_categoria, key=lambda c: len(per_categoria[c]))
            if max_productes:
                seleccio, total = [], 0
                for c in ordre:
                    if total + len(per_categoria[c]) > max_productes:
                        continue
                    seleccio.append(c)
                    total += len(per_categoria[c])
                ordre = seleccio
            print(f"\nPas B: {sum(len(per_categoria[c]) for c in ordre)} productes en {len(ordre)} categories")

            vocabularis = construir_vocabularis(atributs)
            lots_fallits_seguits = 0
            for categoria in ordre:
                productes = ordre_barrejat(per_categoria[categoria])
                print(f"\n── {categoria}: {len(productes)} productes nous "
                      f"(vocabulari: {len(vocabularis[categoria]['productes'])} productes)")
                for i in range(0, len(productes), MIDA_LOT):
                    if time.time() - inici > TEMPS_MAXIM:
                        raise AturadaGemini("Temps maxim del run")
                    lot = productes[i:i + MIDA_LOT]
                    resultat = demanar_atributs(gemini, vocabularis[categoria], lot)
                    if not resultat:
                        lots_fallits_seguits += 1
                        if lots_fallits_seguits >= LLINDAR_LOTS_FALLITS:
                            raise AturadaGemini(f"{LLINDAR_LOTS_FALLITS} lots seguits sense resposta")
                        continue
                    lots_fallits_seguits = 0
                    files_noves = []
                    for p in lot:
                        a = resultat.get(p['id'])
                        if not a:
                            continue
                        a['categoria'] = categoria
                        atributs[(p['supermercat'], p['producte'])] = a
                        vocabularis[categoria]['productes'][a['producte']][a['variant']] += 1
                        if a['marca']:
                            vocabularis[categoria]['marques'][a['marca']] += 1
                        marques.apuntar_candidata(a['marca'], p['supermercat'], a['marca_blanca'])
                        files_noves.append([p['supermercat'], p['producte'], categoria, a['marca'],
                                            a['producte'], a['variant'], a['marca_blanca'], a['unitats'],
                                            a['mida'], a['unitat'], str(date.today())])
                    # Es desa despres de cada lot: si el run s'atura, no es perd la feina feta
                    ws_atributs.append_rows(files_noves, value_input_option='RAW')
                    print(f"   lot {i // MIDA_LOT + 1}: {len(files_noves)}/{len(lot)} desats | "
                          f"tokens sortida acumulats {gemini.tokens_sortida}")
        except AturadaGemini as e:
            motiu_aturada = str(e)
            print(f"\n🛑 {motiu_aturada}. El que s'ha fet ja esta desat; es continua amb la comparacio.")

        if marques.noves:
            ws_marques.append_rows([[m, s, 'pendent', 'Gemini', str(date.today())] for m, s in marques.noves],
                                   value_input_option='RAW')
            print(f"\nMarques blanques candidates afegides com a 'pendent': {len(marques.noves)}")
            for m, s in marques.noves[:30]:
                print(f"   {s}: {m}")
        print(f"\nTokens Gemini: entrada={gemini.tokens_entrada} sortida={gemini.tokens_sortida}")
        if motiu_aturada:
            print(f"⚠️  Run incomplet: {motiu_aturada}")

    files = comparar(preus, atributs, marques)
    desar_comparacions(sheet, files)
    per_tipus = Counter(f[0] for f in files)
    print(f"\n✅ Comparacions_v3: {len(files)} comparacions {dict(per_tipus)}")
    print(f"   Productes amb atributs: {sum(1 for p in preus if (p['supermercat'], p['producte']) in atributs)}"
          f"/{len(preus)}")


if __name__ == '__main__':
    main()
