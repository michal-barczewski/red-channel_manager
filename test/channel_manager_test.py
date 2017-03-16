import argparse
import unittest

from cogs.channel_manager import find_free_numbers


class TestUtils(unittest.TestCase):

    def test_find_free_numbers(self):
        no_free_numbers = [1, 2, 3, 4]

        self.assertEquals([], find_free_numbers(no_free_numbers, 0))
        self.assertEquals([5], find_free_numbers(no_free_numbers, 1))
        self.assertEquals([5, 6], find_free_numbers(no_free_numbers, 2))

        free_numbers = [3, 4, 8]
        self.assertEquals([1, 2, 5, 6, 7], find_free_numbers(free_numbers, 0))
        self.assertEquals([1, 2, 5, 6, 7], find_free_numbers(free_numbers, 1))
        self.assertEquals([1, 2, 5, 6, 7, 9, 10], find_free_numbers(free_numbers, 7))


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