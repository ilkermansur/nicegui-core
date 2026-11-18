from pathlib import Path

CONTRACT_VERSION = "1.0"
KERNEL_DIR = Path(__file__).resolve().parent.parent


class NguiError(Exception):
    """An error the CLI prints as the core locale text `key`, formatted with `vars`."""

    def __init__(self, key: str, **vars):
        super().__init__(key)
        self.key, self.vars = key, vars
