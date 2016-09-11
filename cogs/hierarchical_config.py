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
        current_location = self.data # type: Location
        for key in path:
            if key not in current_location.locations:
                current_location.locations[key] = Location()
            current_location = current_location.locations[key]
        return current_location

    def get_location(self, path: List[str]):
        location = self.data
        for key in path:
            if key in location.locations[key]:
                location = location.locations[key]
        return location

    def save_var(self, path: List[str], name: str, value: ValueType):
        location = self.ensure_path(path)
        location.values[name] = value

    def delete_var(self, path: List[str], name: str):
        location = self.get_location(path)
        if name in location.values[name]:
            del location.values[name]

    def get_var(self, path: List[str], name: str):
        value = self.data.get(name, default=self.defaults.get(name))
        location = self.data
        for key in path:
            # get value from current location, preserve existing one if it doesn't exist here
            value = location.values.get(name, default=location)
            if key in location.locations:
                location = location.locations[key]
            else:
                break
        return value

