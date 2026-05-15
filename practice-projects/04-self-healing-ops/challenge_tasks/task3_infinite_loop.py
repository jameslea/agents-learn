def count_to_three():
    values = []
    current = 0
    while current < 3:
        # 故意遗漏 current += 1，用来测试 timeout 分类和循环修复能力。
        values.append(current)
    return values


if __name__ == "__main__":
    assert count_to_three() == [0, 1, 2]
    print("task3 ok")
