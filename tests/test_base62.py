import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encodes_zero_and_alphabet_boundaries(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_round_trips_large_non_negative_integers(self):
        for value in (1, 62, 3844, 2**63 - 1):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_rejects_negative_or_non_integer_input(self):
        for value in (-1, True, 1.5, "1"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    encode(value)

    def test_rejects_empty_or_invalid_encoded_values(self):
        for value in ("", "!", "a "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode(value)

    def test_rejects_non_string_encoded_values(self):
        with self.assertRaises(TypeError):
            decode(1)


if __name__ == "__main__":
    unittest.main()
