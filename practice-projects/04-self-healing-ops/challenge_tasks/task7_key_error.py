def get_user_email(users, user_id):
    return users[user_id]["email"]


if __name__ == "__main__":
    users = {
        "u1": {"email": "u1@example.com"},
        "u2": {},
    }
    assert get_user_email(users, "u1") == "u1@example.com"
    assert get_user_email(users, "u2") is None
    assert get_user_email(users, "missing") is None
    print("task7 ok")
