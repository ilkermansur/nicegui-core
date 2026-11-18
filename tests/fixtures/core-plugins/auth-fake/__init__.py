class _Auth:
    def current_user(self):
        return {"id": "local", "name": "admin", "roles": ["admin"]}

    def has(self, permission):
        return True


def setup(ctx):
    return _Auth()
