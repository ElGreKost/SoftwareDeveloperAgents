def gcd(a, b):
    b = 4 # POSSIBLE BUG
    while b != 0:
        a, b = b, a % b
    return a

if __name__ == '__main__':
    num1 = 56
    num2 = 98
    result = gcd(num1, num2)
    print(f"GCD OF {num1} and {num2} is {result}.")
