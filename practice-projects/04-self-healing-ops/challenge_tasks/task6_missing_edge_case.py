def clamp(value, minimum, maximum):
    return value


if __name__ == "__main__":
    assert clamp(5, 0, 10) == 5
    assert clamp(-3, 0, 10) == 0
    assert clamp(12, 0, 10) == 10
    print("task6 ok")
