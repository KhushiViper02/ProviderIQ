import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from provideriq.validate import (normalize_phone, valid_email, postcode_state_ok,
                                 grounded, validate, status_for, find_duplicates)


class T(unittest.TestCase):
    def test_phone(self):
        self.assertEqual(normalize_phone("(02) 5550 0101"), "02 5550 0101")
        self.assertEqual(normalize_phone("0412345678"), "0412 345 678")
        self.assertEqual(normalize_phone("1800 555 010"), "1800 555 010")
        self.assertEqual(normalize_phone("12345"), "")

    def test_email(self):
        self.assertTrue(valid_email("a@b.com.au"))
        self.assertFalse(valid_email("not-an-email"))

    def test_postcode_state(self):
        self.assertTrue(postcode_state_ok("NSW", "2000"))
        self.assertFalse(postcode_state_ok("VIC", "2000"))
        self.assertTrue(postcode_state_ok("ACT", "2600"))
        self.assertIsNone(postcode_state_ok("NSW", "abc"))

    def test_grounding_catches_invented_phone(self):
        text = "Call us on 02 5550 0101 at 22 Wharf Road Sydney NSW 2000"
        self.assertTrue(grounded("phone", "02 5550 0101", text))
        self.assertFalse(grounded("phone", "02 5550 9999", text))

    def test_hallucinated_field_blocks_verified(self):
        text = "Test Clinic 5 High St, Town NSW 2250 call 02 5550 0101 a@b.com"
        rec = dict(name="Test Clinic", type="clinic", address="5 High St", suburb="Town",
                   state="NSW", postcode="2250", phone="02 5550 9999", email="a@b.com",
                   website="x", services=["a"])
        out = validate(rec, text)
        self.assertIn("ungrounded_phone", out["flags"])
        self.assertNotEqual(status_for(out), "verified")

    def test_duplicates(self):
        a = {"name": "Harbourview Medical Centre", "postcode": "2000"}
        b = {"name": "Harbour View Medical Centre", "postcode": "2000"}
        find_duplicates([a, b])
        self.assertEqual(b.get("duplicate_of"), "Harbourview Medical Centre")


if __name__ == "__main__":
    unittest.main()
