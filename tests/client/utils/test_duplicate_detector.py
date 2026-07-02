import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'client'))

from utils.duplicate_detector import (
    extract_preview_duplicate_key,
    find_preview_duplicates,
    filter_duplicate_indices,
)


class TestDuplicateDetector(unittest.TestCase):
    def test_dict_with_product_id(self):
        row = {'product_id': 5, 'customer_code': 'C001', 'oe_number': 'OE123'}
        key, display = extract_preview_duplicate_key(row)
        self.assertEqual(key, 'product_id:5')
        self.assertEqual(display, 'C001')

    def test_dict_without_product_id(self):
        row = {'customer_code': 'C001', 'oe_number': 'OE123'}
        key, display = extract_preview_duplicate_key(row)
        self.assertEqual(key, 'code_oe:C001|OE123')
        self.assertEqual(display, 'C001')

    def test_list_with_model(self):
        row = ['A', 'C001', '10']
        headers = ['No', 'Model', 'Qty']
        key, display = extract_preview_duplicate_key(row, headers=headers, model_col_idx=1)
        self.assertEqual(key, 'model:C001')
        self.assertEqual(display, 'C001')

    def test_empty_row_returns_empty_key(self):
        key, display = extract_preview_duplicate_key({})
        self.assertEqual(key, '')
        self.assertEqual(display, '')

    def test_find_duplicates(self):
        rows = [
            {'product_id': 1},
            {'product_id': 2},
            {'product_id': 1},
        ]
        dups = find_preview_duplicates(rows)
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]['indices'], [0, 2])
        self.assertFalse(dups[0]['external'])

    def test_external_existing_keys(self):
        rows = [{'product_id': 1}]
        dups = find_preview_duplicates(rows, existing_keys={'product_id:1'})
        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0]['indices'], [0])
        self.assertTrue(dups[0]['external'])

    def test_filter_duplicate_indices_keep_first(self):
        rows = [{'product_id': 1}, {'product_id': 2}, {'product_id': 1}]
        dups = find_preview_duplicates(rows)
        keep = filter_duplicate_indices(len(rows), dups)
        self.assertEqual(keep, [0, 1])

    def test_filter_duplicate_indices_skip_external(self):
        rows = [{'product_id': 1}]
        dups = find_preview_duplicates(rows, existing_keys={'product_id:1'})
        keep = filter_duplicate_indices(len(rows), dups)
        self.assertEqual(keep, [])


if __name__ == '__main__':
    unittest.main()
