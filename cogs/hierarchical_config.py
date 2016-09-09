from typing import Dict, List


class HierarchicalConfig:
    def __init__(self, defaults: Dict[str, object] = {}):
        self.data = {}
        self.defaults = defaults

    def ensure_path(self, path: List[str]) -> Dict[str, Dict]:
        if len(path) == 0:
            return self.data
        current_location = self.data
        for key in path:
            if key not in current_location:
                current_location[key] = dict()
            current_location = current_location[key]
        return current_location

    def save_var(self, name, value, path):
        location = self.ensure_path(path)
        location[name] = value

    def get_var(self, name, path):
        pass
