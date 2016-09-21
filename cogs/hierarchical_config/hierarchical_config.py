import logging
from typing import Dict, Iterable, List, Set, Union, NewType

try:
    import jsonpickle
except ImportError:
    jsonpickle = None

BaseValueType = NewType('BaseValueType', Union[str, int, float])
ValueType = NewType('ValueType', Union[BaseValueType, List[BaseValueType], Set[BaseValueType], Dict[str, BaseValueType]])

logger = logging.getLogger("red.hierarchical_config")
logger.setLevel(logging.DEBUG)


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
        self.data = data if data else Location()  # type: Location
        self.defaults = defaults if defaults else {}  # type: Dict[str, ValueType]

    def __eq__(self, other):
        if not isinstance(other, HierarchicalConfig):
            return False
        elif self.defaults != other.defaults:
            return False
        else:
            return self.data == self.data

    def ensure_path(self, path: List[str]) -> Location:
        if path is None or len(path) == 0:
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

    def set_var(self, name: str, value: ValueType, path: List[str] = None):
        if isinstance(value, (str, int, float, List, Set, Dict)):
            location = self.ensure_path(path)
            location.values[name] = value
        else:
            raise TypeError('value should be one of following types: str, int, float, List, Set, Dict')

    def delete_var(self, path: List[str], name: str):
        location = self.get_location(path)
        if name in location.values[name]:
            del location.values[name]

    def get_var(self, name: str, path: Iterable[str] = None) -> ValueType:
        """Retrieve variable value from specified path

        If value doesn't exist at specified path, value is looked up recursively at lower levels,
        stoping at default value

        If variable is of mutable type then a copy of it will be returned, to modify it use set_var with copy as value

        :param name: name of the variable to retrieve
        :param path: path of the variable
        :return: value of the variable
        """

        value = self.data.values.get(name, self.defaults.get(name))
        location = self.data
        if not path:
            return value
        for key in path:
            # get value from current location, preserve existing one if it doesn't exist here
            if key in location.locations:
                location = location.locations[key]
                value = location.values.get(name, value)
            else:
                break
        logger.debug('retrieved variable {0!r}: value {1!r}, type {2!r}'.format(name, value, type(value)))
        if isinstance(value,(str, int, float)) or value is None:
            return value
        elif isinstance(value,(List,Set,Dict)):
            return value.copy()
        else:
            raise TypeError('tried to retrieve value of unsupported type (this should not be possible)')

    def save(self, file_name: str):
        with open(file_name, 'w+') as config_file:
            jsonpickle.set_preferred_backend('simplejson')
            jsonpickle.set_encoder_options('simplejson', sort_keys=True, indent=4)
            json_str = jsonpickle.encode(self.data)
            config_file.write(json_str)

    def load(self, file_name: str):
        with open(file_name, 'r') as config_file:
            json_str = config_file.read()
            self.data = jsonpickle.decode(json_str)


class VariableNotInLevel(Exception):
    pass


class Variable:

    def __init__(self, name: str,
                 levels: List[str],
                 var_type: str,
                 description: str,
                 default: str,
                 store: HierarchicalConfig):
        self.name = name
        self.levels = levels
        self.var_type = var_type
        self.description = description
        self.default = default
        self.store = store  # type: HierarchicalConfig

    def _convert_value(self, value):
        if self.var_type == 'int':
            return int(value)

    def _convert_and_set_value(self, value, path):
        try:
            converted = self._convert_value(value)
            self.store.set_var(self.name, converted, path=path)
        except Exception as e:
            raise e

    def set_global(self, value):
        if 'global' not in self.levels:
            raise VariableNotInLevel(level='global')
        self._convert_and_set_value(value, None)

    def set_server(self, server, value):
        if 'server' not in self.levels:
            raise VariableNotInLevel(level='server')
        self._convert_and_set_value(value, [server.id])

    def set_group(self, server, group_name, value):
        if 'group' not in self.levels:
            raise VariableNotInLevel(level='group')
        self._convert_and_set_value(value, [server.id, group_name])

    def get(self, path: List[str]=None):
        return self.store.get_var(name=self.name, path=path)


def setup(bot):
    if jsonpickle is None:
        raise RuntimeError("You need to run `pip3 install jsonpickle`")
