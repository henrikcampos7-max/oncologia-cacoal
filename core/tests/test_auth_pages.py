from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class PublicPagesTests(SimpleTestCase):
    def test_login_uses_oncologia_cacoal_brand_and_safe_fields(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Oncologia Cacoal")
        self.assertContains(response, "Gestão segura de tratamentos oncológicos")
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertNotContains(response, "@gmail.com")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class AccessRequestPageTests(TestCase):
    def test_access_request_does_not_collect_credentials(self):
        response = self.client.get(reverse("solicitar_acesso"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar acesso")
        self.assertContains(response, "Um administrador analisará a solicitação")
