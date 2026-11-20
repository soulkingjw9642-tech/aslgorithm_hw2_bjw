import unittest

from src.hash_table import HashTable, LinearProbingHashTable


class HashTableTests(unittest.TestCase):
    table_class = HashTable
    empty_miss_probes = 0

    def test_empty_table_and_missing_key(self):
        table = self.table_class(capacity=4)
        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertEqual(
            table.find_with_probes("missing"), (None, self.empty_miss_probes)
        )
        self.assertEqual(len(table.probe_trace("missing")), self.empty_miss_probes)

    def test_collisions_are_stored_and_found(self):
        table = self.table_class(capacity=3)
        self.assertEqual(table.bucket_index("first"), table.bucket_index("second"))
        self.assertEqual(table.bucket_index("first"), table.bucket_index("missing"))
        table.put("first", "one")
        table.put("second", "two")
        self.assertEqual(table.get("first"), "one")
        self.assertEqual(table.get("second"), "two")
        self.assertEqual(table.find_with_probes("second"), ("two", 2))
        self.assertEqual(len(table.probe_trace("second")), 2)
        self.assertEqual(
            table.find_with_probes("missing"),
            (None, 2 if self.table_class is HashTable else 3),
        )

    def test_duplicate_key_updates_without_changing_size(self):
        table = self.table_class(capacity=3)
        table.put("key", "old")
        table.put("key", "new")
        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_items_contains_each_key_value_pair(self):
        table = self.table_class(capacity=3)
        table.put("a", "1")
        table.put("b", "2")
        self.assertCountEqual(list(table.items()), [("a", "1"), ("b", "2")])

    def test_stores_and_finds_entries_across_capacities(self):
        for capacity in (2, 3, 7):
            with self.subTest(capacity=capacity):
                table = self.table_class(capacity=capacity)
                table.put("first", "one")
                table.put("second", "two")
                self.assertEqual(table.get("first"), "one")
                self.assertEqual(table.get("second"), "two")

    def test_horner_hash_and_trace_explain_the_bucket(self):
        table = self.table_class(capacity=7)
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
                    self.table_class(capacity=capacity)

    def test_rejects_non_string_keys_and_values(self):
        table = self.table_class(capacity=2)
        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.put("key", 1)
        with self.assertRaises(TypeError):
            table.get(1)


class LinearProbingHashTableTests(HashTableTests):
    table_class = LinearProbingHashTable
    empty_miss_probes = 1

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = LinearProbingHashTable(capacity=4)
        colliding_keys = []
        for number in range(1000):
            key = f"key-{number}"
            if table.bucket_index(key) == table.capacity - 1:
                colliding_keys.append(key)
                if len(colliding_keys) == 2:
                    break

        self.assertEqual(len(colliding_keys), 2)
        table.put(colliding_keys[0], "one")
        table.put(colliding_keys[1], "two")
        self.assertEqual(table.buckets[3], ((colliding_keys[0], "one"),))
        self.assertEqual(table.buckets[0], ((colliding_keys[1], "two"),))
        self.assertEqual(table.probe_trace(colliding_keys[1]), (3, 0))
        self.assertEqual(table.find_with_probes(colliding_keys[1]), ("two", 2))

    def test_full_table_finds_all_entries_and_rejects_an_extra_key(self):
        table = LinearProbingHashTable(capacity=3)
        entries = (("first", "one"), ("second", "two"), ("third", "three"))
        for key, value in entries:
            table.put(key, value)

        self.assertEqual(len(table), table.capacity)
        for key, value in entries:
            self.assertEqual(table.get(key), value)
        table.put("first", "updated")
        self.assertEqual(table.get("first"), "updated")
        self.assertEqual(len(table), table.capacity)
        self.assertEqual(table.find_with_probes("missing"), (None, table.capacity))
        self.assertEqual(len(table.probe_trace("missing")), table.capacity)
        with self.assertRaises(OverflowError):
            table.put("extra", "value")


if __name__ == "__main__":
    unittest.main()
