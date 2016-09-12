import json
import unittest

import jsonpickle

from cogs.hierarchical_config import HierarchicalConfig, Location


class TestSettings(unittest.TestCase):

    def testEnsurePath(self):
        config = HierarchicalConfig()

        self.assertDictEqual({}, config.data.locations)

        path = []
        config.ensure_path(path)
        self.assertDictEqual({}, config.data.locations)

        path = ['a1']
        config.ensure_path(path)
        self.assertEqual({'a1': Location()}, config.data.locations)

        path = ['a1', 'b1']
        config.ensure_path(path)
        self.assertEqual({
            'a1': Location({
                'b1': Location()
            })
        }, config.data.locations)

        path = ['a2', 'b2']
        config.ensure_path(path)
        self.assertDictEqual({
            'a1': Location({
                'b1': Location()
            }),
            'a2': Location({
                'b2': Location()
            })
        }, config.data.locations)

        path = ['a1', 'b1', 'c1']
        config.ensure_path(path)
        self.assertDictEqual({
            'a1': Location({
                'b1': Location({
                    'c1': Location()
                })
            }),
            'a2': Location({
                'b2': Location()
            })
        }, config.data.locations)

    def testConfig(self):
        config = HierarchicalConfig()

        path = ['a1', 'b1', 'c1']
        config.ensure_path(path)

        location = config.get_location(['a1', 'b1'])
        self.assertEqual(Location({'c1': Location()}), location)

        value = 123
        name = "abc"
        config.save_var(path, name, value)

        read_value = config.get_var(path, name)
        self.assertEquals(123, read_value)

        config.save_var([],"name", "v_root")
        config.save_var(['lvl_1_a'], "name", "v_1a")

        default_value = config.get_var(['lvl_1_b'], 'name')
        self.assertEquals('v_root', default_value)

        lvl_1_value = config.get_var(['lvl_1_a'], 'name')
        self.assertEquals('v_1a', lvl_1_value)

        lvl_2_value = config.get_var(['lvl_1_a', 'lvl_2_a'], 'name')
        self.assertEquals('v_1a', lvl_2_value)

        other_lvl_value = config.get_var(['a', 'b', 'c', 'd'], 'name')
        self.assertEquals('v_root', other_lvl_value)

        config.save_var([], 'other_name', 1)
        other_name_value = config.get_var(['1'], 'other_name')
        self.assertEquals(1, other_name_value)

    def testJsonSerialize(self):
        config = HierarchicalConfig()

        config.save_var([], 'var1', 1)
        config.save_var(['a1', 'b1'], 'var2', 'abc')
        config.save_var(['a1'], 'var3', [1,2,3])

        json_str = jsonpickle.encode(config)

        loaded_config = jsonpickle.decode(json_str)

        self.assertEquals(config, loaded_config)

if __name__ == '__main__':
    unittest.main()