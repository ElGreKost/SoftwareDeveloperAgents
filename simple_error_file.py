def gcd(a, b):
    # Fix the bug by setting b to the correct input parameter a
    b = a

    while b != 0:
        a, b = b, a % b
    return a

if __name__ == '__main__':
    # Παράδειγμα χρήσης
    num1 = 56
    num2 = 98
    result = gcd(num1, num2)
    print(f"Το ΜΚΔ των {num1} και {num2} είναι {result}.")
