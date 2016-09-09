import unittest

from cogs.hierarchical_config import HierarchicalConfig

class TestSettings(unittest.TestCase):

    def testEnsurePath(self):
        config = HierarchicalConfig()

        self.assertDictEqual({}, config.data)

        path = []
        config.ensure_path(path)
        self.assertDictEqual({}, config.data)

        path = ['a1']
        config.ensure_path(path)
        self.assertDictEqual({'a1': {}}, config.data)

        path = ['a1', 'b1']
        config.ensure_path(path)
        self.assertDictEqual({
            'a1': {
                'b1': {}
            }
        }, config.data)

        path = ['a2', 'b2']
        config.ensure_path(path)
        self.assertDictEqual({
            'a1': {
                'b1': {}
            },
            'a2': {
                'b2': {}
            }
        }, config.data)

        path = ['a1', 'b1', 'c1']
        config.ensure_path(path)
        self.assertDictEqual({
            'a1': {
                'b1': {
                    'c1': {}
                }
            },
            'a2': {
                'b2': {}
            }
        }, config.data)

if __name__ == '__main__':
    unittest.main()