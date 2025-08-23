import unittest

class TestMyFunctionality(unittest.TestCase):
    def test_case_1(self):
        self.assertEqual(my_function(2, 3), 5)

    def test_case_2(self):
        self.assertTrue(isinstance(my_function(2, 3), int))