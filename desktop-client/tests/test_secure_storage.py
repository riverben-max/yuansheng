from __future__ import annotations

import os
import unittest

from secure_storage import SecureStorageError, protect_text, unprotect_text


@unittest.skipUnless(os.name == "nt", "DPAPI secure storage is only available on Windows")
class SecureStorageTests(unittest.TestCase):
    def test_protected_text_round_trips_without_plaintext(self) -> None:
        plaintext = "secret-cookie=hidden; _m_h5_tk=abc_1777188499080; sn=x"

        protected = protect_text(plaintext)

        self.assertNotEqual(protected, plaintext)
        self.assertTrue(protected.startswith("dpapi:v1:"))
        self.assertEqual(unprotect_text(protected), plaintext)

    def test_protect_text_rejects_empty_value(self) -> None:
        with self.assertRaisesRegex(SecureStorageError, "empty"):
            protect_text("")

    def test_unprotect_text_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(SecureStorageError, "decrypt"):
            unprotect_text("dpapi:v1:not-base64")


if __name__ == "__main__":
    unittest.main()
