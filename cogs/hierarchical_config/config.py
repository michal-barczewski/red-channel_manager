import json
import logging
import os
from collections import defaultdict, ChainMap
from typing import Dict, Iterable, List, Set, Union, NewType

BaseValueType = NewType('BaseValueType', Union[str, int, float])
ValueType = NewType('ValueType', Union[BaseValueType, List[BaseValueType], Set[BaseValueType], Dict[str, BaseValueType]])

logger = logging.getLogger("red.hierarchical_config")
logger.setLevel(logging.DEBUG)


class Config:
    def __init__(self, defaults: Dict[str, ValueType] = None, data: Dict[str,Dict[str,BaseValueType]] = None):
        data = data if data is not None else {}
        self.data = defaultdict(data)
        self.defaults = defaults if defaults is not None else {}  # type: Dict[str, ValueType]

    def __eq__(self, other):
        if not isinstance(other, Config):
            return False
        elif self.defaults != other.defaults:
            return False
        else:
            return self.data == self.data

    def __str__(self):
        return self.__dict__

    def get_location(self, path: List[str]):
        if path is None or len(path) == 0:
            return self.data['']
        location = ChainMap(self.data[''], self.defaults)
        current_path = ''
        for key in path:
            current_path = os.path.join(current_path, key)
            location = location.new_child(self.data[current_path])
        return location

    def set_var(self, name: str, value: ValueType, path: List[str] = None):
        if isinstance(value, (str, int, float, List, Set, Dict)):
            location = self.get_location(path)
            location[name] = value
        else:
            raise TypeError('value should be one of following types: str, int, float, List, Set, Dict')

    def delete_var(self, path: List[str], name: str):
        location = self.get_location(path)
        if name in location[name]:
            del location[name]

    def get_var(self, name: str, path: Iterable[str] = None) -> ValueType:
        """Retrieve variable value from specified path

        If value doesn't exist at specified path, value is looked up at lower levels,

        If variable is of mutable type then a copy of it will be returned, to modify it use set_var with copy as value

        :param name: name of the variable to retrieve
        :param path: path of the variable
        :return: value of the variable
        """

        location = self.get_location(path)
        value = location[name]
        logger.debug('retrieved variable {0!r}: value {1!r}, type {2!r}'.format(name, value, type(value)))
        if isinstance(value, (str, int, float)) or value is None:
            return value
        elif isinstance(value,(List,Set,Dict)):
            return value.copy()
        else:
            raise TypeError('tried to retrieve value of unsupported type (this should not be possible)')

    def save(self, file_name: str):
        with open(file_name, 'w+') as config_file:
            json.dump(self.data, config_file)

    def load(self, file_name: str):
        with open(file_name, 'r') as config_file:
            json_str = config_file.read()
            self.data = json.loads(json_str)


class VariableNotInLevel(Exception):
    pass


class Variable:

    def __init__(self, name: str,
                 levels: List[str],
                 var_type: str,
                 description: str,
                 default: str,
                 store: Config):
        self.name = name
        self.levels = levels
        self.var_type = var_type
        self.description = description
        self.default = default
        self.store = store  # type: Config

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
    pass
