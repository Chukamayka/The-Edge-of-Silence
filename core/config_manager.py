import json
from pathlib import Path


class ConfigManager:
    def __init__(self, path, defaults):
        self.path = Path(path)
        self.defaults = defaults.copy()

    def load(self):
        data = self.defaults.copy()
        if not self.path.exists():
            return data
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return data
        if not isinstance(loaded, dict):
            return data
        for key, default_value in self.defaults.items():
            value = loaded.get(key, default_value)
            if isinstance(default_value, int) and isinstance(value, int):
                data[key] = value
            elif isinstance(default_value, float) and isinstance(value, (int, float)):
                data[key] = float(value)
            else:
                data[key] = default_value
        return data

    def save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {}
        for key, default_value in self.defaults.items():
            value = data.get(key, default_value)
            if isinstance(default_value, int):
                payload[key] = int(value)
            elif isinstance(default_value, float):
                payload[key] = float(value)
            else:
                payload[key] = value
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
