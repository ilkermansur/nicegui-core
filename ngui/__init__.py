from pathlib import Path

CONTRACT_VERSION = "1.0"
KERNEL_DIR = Path(__file__).resolve().parent.parent
LOCALES_DIR = KERNEL_DIR / "ngui" / "locales"  # the kernel's own "core" texts


class NguiError(Exception):
    """An error the CLI prints as the core locale text `key`, formatted with `vars`."""

    def __init__(self, key: str, **vars):
        super().__init__(vars.get("detail", key))
        self.key, self.vars = key, vars
