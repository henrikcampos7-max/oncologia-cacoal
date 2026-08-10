from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class HealthViewTests(SimpleTestCase):
    def test_health_returns_minimal_status(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "ok", "sistema": "Oncologia Cacoal"}
        )
        self.assertEqual(
            response.headers["Cache-Control"],
            "max-age=0, no-cache, no-store, must-revalidate, private",
        )

    def test_health_rejects_post(self):
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)


class ApprovedStackTests(SimpleTestCase):
    def test_database_backend_is_postgresql(self):
        self.assertIn(
            settings.DATABASES["default"]["ENGINE"],
            {"django.db.backends.postgresql", "django.db.backends.sqlite3"},
        )

    def test_locale_is_portuguese_and_manaus(self):
        self.assertEqual(settings.LANGUAGE_CODE, "pt-br")
        self.assertEqual(settings.TIME_ZONE, "America/Manaus")

    def test_password_minimum_is_fifteen(self):
        minimum = next(
            validator
            for validator in settings.AUTH_PASSWORD_VALIDATORS
            if validator["NAME"].endswith("MinimumLengthValidator")
        )
        self.assertEqual(minimum["OPTIONS"]["min_length"], 15)
