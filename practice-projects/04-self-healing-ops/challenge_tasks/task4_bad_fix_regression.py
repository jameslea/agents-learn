def safe_divide(a, b):
    return a / b


if __name__ == "__main__":
    assert safe_divide(8, 2) == 4
    assert safe_divide(8, 0) is None
    print("task4 ok")
