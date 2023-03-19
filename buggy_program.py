def buggy_function():
    num1 = 2
    num2 = int("3")
    return num1 + num2

if __name__ == "__main__":
    print(buggy_function())