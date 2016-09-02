import unittest

from cogs.channel_manager import find_free_numbers

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



if __name__ == '__main__':
    unittest.main()