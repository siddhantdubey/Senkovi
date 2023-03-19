# buggy_program.py
def buggy_function():
    """This function is meant to add two integers together"""
    number2 = 5
    number1 = "4"
    result = number1 + number2
    return result
if __name__ == "__main__":
    print(buggy_function())
