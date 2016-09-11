from typing import Dict, List, TypeVar, Union

BaseValueType = TypeVar('BaseValueType', Union[str, int, float])
ValueType = TypeVar('ValueType', Union[BaseValueType, List[BaseValueType]])


class Location:
    def __init__(self):
        self.locations = dict()  # type: Dict[str, Location]
        self.values = dict()  # type: Dict[str, ValueType]


class HierarchicalConfig:
    def __init__(self, defaults: Dict[str, ValueType] = None):
        self.data = Location()
        self.defaults = {} if defaults is None else defaults # type: Dict[str, ValueType]

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
        value = self.data.get(name, default=self.defaults.get(name))
        location = self.data
        for key in path:
            # get value from current location, preserve existing one if it doesn't exist here
            value = location.get(name, default=location)
            if key in location:
                location = location[key]
            else:
                break
        return value

