import tempfile
import unittest
from pathlib import Path

from app import create_app


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": str(Path(self.tmp.name) / "test.db")})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def search(self, term):
        return self.client.post("/api/search", json={"term": term})

    def test_normal_search_and_health(self):
        self.assertEqual(self.client.get("/health").json["status"], "ok")
        response = self.search("SQL")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["count"], 1)
        self.assertEqual(response.json["results"][0]["name"], "SQL Fundamentals")

    def test_injection_text_cannot_change_query(self):
        for term in ("' OR 1=1 --", "'; DROP TABLE products; --", "%", "_"):
            with self.subTest(term=term):
                response = self.search(term)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["count"], 0)
        self.assertEqual(self.search("SQL").json["count"], 1)

    def test_validation_and_request_limit(self):
        self.assertEqual(self.search("").status_code, 400)
        self.assertEqual(self.search("x" * 81).status_code, 400)
        self.assertEqual(self.search("a\nb").status_code, 400)
        self.assertEqual(self.client.post("/api/search", data="x").status_code, 415)
        limited = create_app({"TESTING": True, "DATABASE": str(Path(self.tmp.name) / "limited.db"), "RATE_LIMIT": 1}).test_client()
        self.assertEqual(limited.post("/api/search", json={"term": "SQL"}).status_code, 200)
        self.assertEqual(limited.post("/api/search", json={"term": "SQL"}).status_code, 429)

    def test_security_headers_and_frontend(self):
        response = self.client.get("/")
        self.assertIn(b"SQLGuard Lab", response.data)
        self.assertIn(b"search-form", response.data)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
