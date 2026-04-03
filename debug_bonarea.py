import re

def extreure_quantitat(nom):
    # Cas pack: "6 x 52 g" -> "6 x 52 g"
    match_pack = re.search(r'(\d+)\s*x\s*(\d+[.,]?\d*)\s*(kg|g|l|ml|cl)', nom, re.IGNORECASE)
    if match_pack:
        return f"{match_pack.group(1)} x {match_pack.group(2)} {match_pack.group(3).lower()}"
    # Cas normal: última quantitat
    matches = re.findall(r'(\d+[.,]?\d*)\s*(kg|g|l|ml|cl|ud|unidades?)', nom, re.IGNORECASE)
    if matches:
        val, unitat = matches[-1]
        return f"{val} {unitat.lower()}"
    return ''

# Test
noms = [
    'Atun en aceite de girasol Dia Mari Marinera 6 x 52 g',
    'Tomate frito casero Dia Vegecampo 350 g',
    'Agua mineral Dia 1.5 L',
    'Leche semidesnatada Dia pack 6 x 1 L',
    'Patatas fritas Dia 150 g',
]
for nom in noms:
    print(f"  {nom[:50]:<50} -> {extreure_quantitat(nom)}")
