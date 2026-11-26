from pathlib import Path
import tomllib
from typing import Any


class Translator:
    def __init__(
        self,
        locales_dir: Path,
        default_locale: str = "ru",
        fallback_locale: str = "ru",
    ) -> None:
        self._locales_dir = locales_dir
        self._default_locale = default_locale
        self._fallback_locale = fallback_locale
        self._translations: dict[str, dict[str, Any]] = {}
        self._load_all_locales()

    def _load_all_locales(self) -> None:
        if not self._locales_dir.exists():
            return

        for file_path in self._locales_dir.glob("*.toml"):
            with file_path.open("rb") as file:
                self._translations[file_path.stem] = tomllib.load(file)

    def get(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        target_locale = locale or self._default_locale
        template = self._lookup(target_locale, key)

        if template is None and target_locale != self._fallback_locale:
            template = self._lookup(self._fallback_locale, key)

        if template is None:
            return key

        if kwargs:
            return template.format(**kwargs)
        return template

    def _lookup(self, locale: str, dotted_key: str) -> str | None:
        current: Any = self._translations.get(locale)
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]

        return current if isinstance(current, str) else None
