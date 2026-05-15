def average(values):
    return sum(values) / len(values)


if __name__ == "__main__":
    assert average([2, 4, 6]) == 4
    assert average([]) == 0
    print("task8 ok")
