import argparse
import unittest

from cogs.channel_manager import find_free_numbers
from cogs.hierarchical_config import HierarchicalConfig, Variable


class TestUtils(unittest.TestCase):

    def test_find_free_numbers(self):
        no_free_numbers = [1, 2, 3, 4]
        self.assertEquals(find_free_numbers(no_free_numbers, 0), [])
        self.assertEquals(find_free_numbers(no_free_numbers, 1), [5])
        self.assertEquals(find_free_numbers(no_free_numbers, 2), [5, 6])

        free_numbers = [3, 4, 8]
        self.assertEquals(find_free_numbers(free_numbers, 0), [1, 2, 5, 6, 7])
        self.assertEquals(find_free_numbers(free_numbers, 1), [1, 2, 5, 6, 7])
        self.assertEquals(find_free_numbers(free_numbers, 7), [1, 2, 5, 6, 7, 9, 10])

    def test_int_variable(self):
        config = HierarchicalConfig()
        int_variable = Variable(
            levels=['global', 'server', 'group'],
            name='int_variable',
            var_type='int',
            default=1,
            description='minimum time since last activity before channel is allowed to be deleted',
            store=config
        )
        int_variable.set_global(5)
        self.assertEquals(int_variable.get(), 5)
        int_variable.set_global('5')
        self.assertEquals(int_variable.get(), 5)

        self.assertRaises(ValueError, int_variable.set_global, 'a')

    def test_argparse(self):
        parser = argparse.ArgumentParser(prog="set")
        #parser.add_argument('variable_name', type=str, help='name of variable to set')
        parser.add_argument('-level', type=str, default='global',help='specify on what level to set the value')
        parser.add_argument('-channel_timeout', type=int, default=1,help='time since last channel activity before which channel can not be deleted')
        print(
            parser.parse_args(['-level', 'server',
                               '-channel_timeout','1'])
        )
        #parser.print_help()
if __name__ == '__main__':
    unittest.main()