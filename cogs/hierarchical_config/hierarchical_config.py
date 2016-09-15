from typing import Dict, List, Union, NewType

BaseValueType = NewType('BaseValueType', Union[str, int, float])
ValueType = NewType('ValueType', Union[BaseValueType, List[BaseValueType]])


class Location:
    def __init__(self, locations: Dict = None, values: Dict[str, ValueType] = None) -> object:
        self.locations = locations if locations else {}  # type: Dict[str, Location]
        self.values = values if values else {}  # type: Dict[str, ValueType]

    def __eq__(self, other):
        if not isinstance(other, Location):
            return False
        elif self.locations != other.locations:
            return False
        else:
            return self.values == other.values


class HierarchicalConfig:
    def __init__(self, defaults: Dict[str, ValueType] = None, data: Location = None):
        self.data = data if data else Location() # type: Location
        self.defaults = defaults if defaults else {}  # type: Dict[str, ValueType]

    def __eq__(self, other):
        if not isinstance(other, HierarchicalConfig):
            return False
        elif self.defaults != other.defaults:
            return False
        else:
            return self.data == self.data

    def ensure_path(self, path: List[str]) -> Dict[str, Dict]:
        if len(path) == 0:
            return self.data
        location = self.data  # type: Location
        for key in path:
            if key not in location.locations:
                location.locations[key] = Location()
            location = location.locations[key]
        return location

    def get_location(self, path: List[str]):
        location = self.data
        for key in path:
            if key in location.locations:
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
        value = self.data.values.get(name, self.defaults.get(name))
        location = self.data
        for key in path:
            # get value from current location, preserve existing one if it doesn't exist here
            if key in location.locations:
                location = location.locations[key]
                value = location.values.get(name, value)
            else:
                break
        return value
