import unittest
from joblin import *
from slack_bot import *


class TestJoblin(unittest.TestCase):

    def test_fetch_listings(self):
        listings = fetch_listings()
        found = False
        company_name = "Citadel Securities"
        title = "Trading Fundamental Analyst Internship"
        for listing in listings:
            if listing['company_name'] == company_name and \
               listing['title'] == title:
                found = True
                break
        self.assertTrue(found, f"'{title}' not found in fetched listings.")

    def test_get_fields(self):
        fields = get_fields()
        self.assertIsInstance(fields, list, "Fields should be a list.")
        self.assertGreater(len(fields), 0, "Fields list should not be empty.")
        for field in fields:
            self.assertIn('field_name', field,
                          "Field should contain 'field_name'.")
            self.assertIn('id', field, "Field should contain 'id'.")

    def test_add_field(self):
        initial_fields = get_fields()
        new_field_name = "Test Field"
        add_field(new_field_name)
        fields_after_addition = get_fields()
        self.assertGreater(len(fields_after_addition), len(initial_fields),
                           "Field should be added successfully.")
        self.assertIn(new_field_name,
                      [f['field_name'] for f in fields_after_addition],
                      "New field should be present in the fields list.")

    def test_delete_field(self):
        fields = get_fields()

        field_to_delete = fields[0]['id']
        delete_field(field_to_delete)
        fields_after_deletion = get_fields()
        self.assertNotIn(field_to_delete,
                         [f['id'] for f in fields_after_deletion],
                         "Field should be deleted successfully.")
