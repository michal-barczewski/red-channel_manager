import unittest

from cogs.micks_utils import process_input


class TestMicksUtils(unittest.TestCase):

    def testProcesInput(self):
        expected = 'multi word command'

        self.assertEquals(expected, process_input('Multi word command'))

        self.assertEquals(expected, process_input('Multi WOrd   coMMand'))
