from rapidfuzz import fuzz

# Exemple real
a = "Llet semidesnatada Hacendado 1l"
b = "Leche semidesnatada 1L"

print(fuzz.token_sort_ratio(a, b))  # Quina similitud dona?
