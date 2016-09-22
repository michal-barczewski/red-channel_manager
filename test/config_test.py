import json
import os
import unittest


from cogs.config import Config


class TestSettings(unittest.TestCase):

    def testConfig(self):
        config = Config()

        path = ['a1', 'b1', 'c1']

        value = 123
        name = "abc"
        config.set_var(name, value, path)

        read_value = config.get_var(name, path)
        self.assertEquals(123, read_value)

        config.set_var("name", "v_root", [])
        config.set_var("name", "v_1a", ['lvl_1_a'])

        default_value = config.get_var('name', ['lvl_1_b'])
        self.assertEquals('v_root', default_value)

        lvl_1_value = config.get_var('name', ['lvl_1_a'])
        self.assertEquals('v_1a', lvl_1_value)

        lvl_2_value = config.get_var('name', ['lvl_1_a', 'lvl_2_a'])
        self.assertEquals('v_1a', lvl_2_value)

        other_lvl_value = config.get_var('name', ['a', 'b', 'c', 'd'])
        self.assertEquals('v_root', other_lvl_value)

        config.set_var('other_name', 1, [])
        other_name_value = config.get_var('other_name', ['1'])
        self.assertEquals(1, other_name_value)

    def testJsonSerialize(self):
        config = Config()

        config.set_var('var1', 1, [])
        config.set_var('var2', 'abc', ['a1', 'b1'])
        config.set_var('var3', [1, 2, 3], ['a1'])

        json_str = json.dumps(config.data)

        loaded_config = Config(defaults=None, data=json.loads(json_str))

        self.assertEquals(config, loaded_config)

    def testSaveLoad(self):
        config = Config()
        config.set_var('var1', 10, [])
        config.set_var('athing', [{'abc': 234}], ['place'])
        path = './data/'
        if not os.path.exists(path):
            os.mkdir(path)
        file_name = 'config.json'
        file_path = os.path.join(path, file_name)
        config.save(file_path)

        loaded_config = Config()
        loaded_config.load(file_path)

        self.assertEquals(config, loaded_config)


if __name__ == '__main__':
    unittest.main()
