from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from . import util


class WikiTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        settings = override_settings(MEDIA_ROOT=directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.root = Path(directory.name)
        (self.root / "entries").mkdir()
        util.save_entry("Python", "# Python\n\nA **language**.\n\n- One\n- Two\n\n[Docs](https://python.org)")
        util.save_entry("Django", "# Django\n\nA framework.")

    def entry_url(self, title="Python"):
        return reverse("encyclopedia:entry", args=[title])

    def test_index_links_and_sidebar(self):
        response = self.client.get(reverse("encyclopedia:index"))
        for title in util.list_entries():
            self.assertContains(response, f'href="{self.entry_url(title)}"')
        for route in ("new", "random", "search"):
            self.assertContains(response, reverse(f"encyclopedia:{route}"))

    def test_entry_renders_markdown_and_edit_link(self):
        response = self.client.get(self.entry_url())
        for html in ("<title>Python - Wiki</title>", "<h1>Python</h1>",
                     "<strong>language</strong>", "<ul>", "<li>One</li>",
                     '<a href="https://python.org">Docs</a>', "<p>"):
            self.assertContains(response, html)
        self.assertContains(response, reverse("encyclopedia:edit", args=["Python"]))

    def test_missing_entry_and_edit_return_error_page(self):
        for url in (self.entry_url("Missing"),
                    reverse("encyclopedia:edit", args=["Missing"])):
            response = self.client.get(url)
            self.assertContains(response, "Page not found", status_code=404)
            self.assertContains(response, "Missing", status_code=404)

    def test_exact_search_redirects_case_insensitively(self):
        response = self.client.get(reverse("encyclopedia:search"), {"q": " python "})
        self.assertRedirects(response, self.entry_url())

    def test_partial_search_links_matching_entries(self):
        response = self.client.get(reverse("encyclopedia:search"), {"q": "YTHO"})
        self.assertContains(response, f'href="{self.entry_url()}"')
        self.assertNotContains(response, self.entry_url("Django"))

    def test_search_with_no_matches_and_empty_query(self):
        response = self.client.get(reverse("encyclopedia:search"), {"q": "missing"})
        self.assertContains(response, "No entries found.")
        response = self.client.get(reverse("encyclopedia:search"))
        self.assertContains(response, self.entry_url())
        self.assertContains(response, self.entry_url("Django"))

    def test_create_page_persists_markdown_and_redirects(self):
        response = self.client.get(reverse("encyclopedia:new"))
        self.assertContains(response, "<textarea")
        content = "# New page\n\nSome Markdown."
        response = self.client.post(reverse("encyclopedia:new"),
                                    {"title": "New page", "content": content})
        self.assertRedirects(response, self.entry_url("New page"))
        self.assertEqual(util.get_entry("New page"), content)
        self.assertEqual((self.root / "entries" / "New page.md").read_text(), content)

    def test_duplicate_title_does_not_overwrite_entry(self):
        original = util.get_entry("Python")
        for title in ("Python", "python", " Python "):
            response = self.client.post(reverse("encyclopedia:new"),
                                        {"title": title, "content": "Replacement"})
            self.assertContains(response, "An entry with this title already exists.")
            self.assertContains(response, "Replacement")
        self.assertEqual(util.get_entry("Python"), original)
        self.assertEqual(util.list_entries(), ["Django", "Python"])

    def test_invalid_and_missing_form_fields_do_not_create_files(self):
        for title in ("../outside", r"..\outside", "/absolute", ".", "", "<script>"):
            response = self.client.post(reverse("encyclopedia:new"),
                                        {"title": title, "content": "unsafe"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        response = self.client.post(reverse("encyclopedia:new"), {"title": "Blank"})
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(util.list_entries(), ["Django", "Python"])
        self.assertFalse((self.root / "outside.md").exists())

    def test_edit_prefills_raw_markdown(self):
        response = self.client.get(reverse("encyclopedia:edit", args=["Python"]))
        self.assertEqual(response.context["form"].initial["content"], util.get_entry("Python"))
        self.assertContains(response, "# Python")

    def test_edit_saves_without_allowing_title_change(self):
        content = "# Updated\n\n<script>not executable</script>"
        response = self.client.post(reverse("encyclopedia:edit", args=["python"]),
                                    {"title": "../outside", "content": content})
        self.assertRedirects(response, self.entry_url())
        self.assertEqual(util.get_entry("Python"), content)
        self.assertEqual(util.list_entries(), ["Django", "Python"])

    def test_invalid_edit_preserves_existing_content(self):
        original = util.get_entry("Python")
        response = self.client.post(reverse("encyclopedia:edit", args=["Python"]),
                                    {"content": ""})
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(util.get_entry("Python"), original)

    def test_random_page_redirects_to_selected_entry(self):
        with patch("encyclopedia.views.random.choice", return_value="Django") as choice:
            response = self.client.get(reverse("encyclopedia:random"))
        choice.assert_called_once_with(["Django", "Python"])
        self.assertRedirects(response, self.entry_url("Django"))

    def test_random_and_index_handle_empty_encyclopedia(self):
        for filename in (self.root / "entries").iterdir():
            filename.unlink()
        self.assertContains(self.client.get(reverse("encyclopedia:index")), "No entries found.")
        self.assertContains(self.client.get(reverse("encyclopedia:random")),
                            "Page not found", status_code=404)

    def test_html_and_unsafe_markdown_links_are_sanitized(self):
        util.save_entry("Unsafe", '# Unsafe\n\n<script>alert(1)</script>\n\n'
                        '<img src=x onerror="alert(2)">\n\n'
                        '[bad](javascript:alert(3))\n\n'
                        '<a href="data:text/html,bad" onclick="alert(4)">bad</a>')
        response = self.client.get(self.entry_url("Unsafe"))
        for unsafe in ("<script", "<img", "onerror=", "onclick=", "javascript:", "data:text"):
            self.assertNotContains(response, unsafe)
        self.assertContains(response, "<h1>Unsafe</h1>")

    def test_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("encyclopedia:new"),
                                     {"title": "CSRF", "content": "test"}).status_code, 403)
        self.assertEqual(client.post(reverse("encyclopedia:edit", args=["Python"]),
                                     {"content": "test"}).status_code, 403)
        self.assertIsNone(util.get_entry("CSRF"))

    def test_empty_existing_entry_is_not_a_missing_page(self):
        util.save_entry("Empty", "")
        self.assertEqual(self.client.get(self.entry_url("Empty")).status_code, 200)

    def test_read_only_routes_reject_post(self):
        for url in (reverse("encyclopedia:index"), reverse("encyclopedia:search"),
                    reverse("encyclopedia:random"), self.entry_url()):
            self.assertEqual(self.client.post(url).status_code, 405)

    def test_storage_ignores_non_markdown_files(self):
        (self.root / "entries" / "notes.txt").write_text("Not an entry")
        self.assertEqual(util.list_entries(), ["Django", "Python"])
        self.assertIsNone(util.get_entry("Missing"))
