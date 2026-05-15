import requestz


def normalize_status(status):
    return status.strip().lower()


if __name__ == "__main__":
    assert normalize_status(" OK ") == "ok"
    print("task1 ok")
