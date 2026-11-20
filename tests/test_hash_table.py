import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_and_missing_key(self):
        table = HashTable(capacity=4)
        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.find_with_probes("missing"), (None, 0))

    def test_collisions_are_stored_and_found(self):
        table = HashTable(capacity=1)
        table.put("first", "one")
        table.put("second", "two")
        self.assertEqual(table.get("first"), "one")
        self.assertEqual(table.get("second"), "two")
        self.assertEqual(table.find_with_probes("second"), ("two", 2))
        self.assertEqual(table.find_with_probes("missing"), (None, 2))

    def test_duplicate_key_updates_without_changing_size(self):
        table = HashTable(capacity=3)
        table.put("key", "old")
        table.put("key", "new")
        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_items_contains_each_key_value_pair(self):
        table = HashTable(capacity=2)
        table.put("a", "1")
        table.put("b", "2")
        self.assertCountEqual(list(table.items()), [("a", "1"), ("b", "2")])

    def test_horner_hash_and_trace_explain_the_bucket(self):
        table = HashTable(capacity=7)
        trace = table.hash_trace("ab")
        expected = (
            ("a", ord("a"), ord("a") % 7),
            ("b", ord("b"), (ord("a") % 7 * 31 + ord("b")) % 7),
        )
        self.assertEqual(trace, expected)
        self.assertEqual(table.bucket_index("ab"), expected[-1][2])
        self.assertEqual(table.bucket_index(""), 0)

    def test_rejects_invalid_capacity(self):
        for capacity in (0, -1, True, 1.5):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    HashTable(capacity=capacity)

    def test_rejects_non_string_keys_and_values(self):
        table = HashTable(capacity=2)
        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.put("key", 1)
        with self.assertRaises(TypeError):
            table.get(1)


if __name__ == "__main__":
    unittest.main()
