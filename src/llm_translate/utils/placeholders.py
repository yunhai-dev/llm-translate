from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PlaceholderStore:
    values: dict[str, str] = field(default_factory=dict)

    def add(self, prefix: str, value: str) -> str:
        key = f"__{prefix}_{len(self.values)}__"
        self.values[key] = value
        return key

    def restore(self, text: str) -> str:
        restored = text
        for key, value in self.values.items():
            restored = restored.replace(key, value)
        return restored
