class _Store:
    def __init__(self, data, scope):
        self._data, self._scope = data, scope
        self.shared = self if scope[1] == "shared" else _Store(data, (scope[0], "shared"))

    def _k(self, key):
        return (*self._scope, key)

    def get(self, key, default=None):
        return self._data.get(self._k(key), default)

    def set(self, key, value):
        self._data[self._k(key)] = value

    def delete(self, key):
        self._data.pop(self._k(key), None)

    def list(self, prefix=""):
        return sorted(k[2] for k in self._data if k[:2] == self._scope and k[2].startswith(prefix))

    def for_user(self, user_id):
        return _Store(self._data, (self._scope[0], f"user:{user_id}"))


class _Storage:
    def __init__(self):
        self._data = {}

    def for_plugin(self, plugin_id):
        return _Store(self._data, (plugin_id, "local"))

    def purge(self, plugin_id):
        for k in [k for k in self._data if k[0] == plugin_id]:
            del self._data[k]


def setup(ctx):
    return _Storage()
