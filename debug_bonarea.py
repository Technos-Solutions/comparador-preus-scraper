# Afegeix al final del debug_bonarea.py existent
categories_valides = [
    'frescos', 'alimentaci', 'begudes', 'congelats',
    'ctics', 'cura', 'neteja', 'per la llar',
    'mascotes', 'nadons', 'parafarm',
]

categories_trobades = []
for text, uuid in [
    ('Frescos', 'c95cfbf2'), ('Alimentació', 'c49d1ef2'),
    ('Làctics i ous', '8e6bb6f8'), ('Cura personal', 'b2c9fc2f'),
    ('Per la llar', '6ea50412'), ('Espai mascotes', '503fab97'),
    ('Parafarmàcia', '402b37ee'), ('Novetats', '2068f9ba'),
    ('Celler', '5aebd367'), ('Ofertes', '5de4976b'),
]:
    t = text.lower()
    match = any(cat in t for cat in categories_valides)
    print(f'{"✅" if match else "❌"} {text}')
