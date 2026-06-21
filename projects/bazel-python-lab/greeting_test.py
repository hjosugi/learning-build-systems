import unittest

from greeting import greeting


class GreetingTest(unittest.TestCase):
    def test_greeting(self) -> None:
        self.assertEqual(greeting("Bazel"), "hello, Bazel")

    def test_blank_name_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            greeting(" ")


if __name__ == "__main__":
    unittest.main()

