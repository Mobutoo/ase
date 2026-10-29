from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from requests import HTTPError

from .github_adapter import GitHubAdapter
from .grocy_adapter import GrocyAdapter
from .http import adapter_http, github_http, validate_file, validate_url
from .mealie_adapter import MealieAdapter
from .plane_adapter import PlaneAdapter
from .superproductivity_adapter import SuperProductivityAdapter


@override_settings(ADAPTER_ALLOWED_ORIGINS=[], ADAPTER_ALLOWED_FILES=[])
class AdapterNetworkPolicyTests(SimpleTestCase):
    def test_custom_network_adapters_deny_unapproved_origins_at_construction(self):
        constructors = [
            (PlaneAdapter, {"api_url": "http://127.0.0.1", "api_key": "key", "workspace_slug": "work", "project_id": "1"}),
            (MealieAdapter, {"api_url": "http://169.254.169.254", "api_key": "key"}),
            (GrocyAdapter, {"api_url": "http://internal.service", "api_key": "key"}),
            (SuperProductivityAdapter, {"sync_url": "https://unapproved.example/export.json"}),
        ]
        with patch("adapters.http.requests.request") as request:
            for constructor, config in constructors:
                with self.subTest(adapter=constructor.__name__), self.assertRaises(ValueError):
                    constructor(config)
            request.assert_not_called()

    @override_settings(ADAPTER_ALLOWED_ORIGINS=["http://mealie:9000", "https://plane.example"])
    def test_operator_approved_selfhost_services_work(self):
        adapter = MealieAdapter({"api_url": "http://mealie:9000", "api_key": "secret"})
        response = Mock(status_code=200)
        response.json.return_value = []
        with patch("adapters.http.requests.request", return_value=response) as request:
            self.assertEqual(adapter._get("/api/groups/mealplans"), [])
        request.assert_called_once()
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        self.assertEqual(request.call_args.args[:2], ("GET", "http://mealie:9000/api/groups/mealplans"))

    @override_settings(ADAPTER_ALLOWED_ORIGINS=["https://approved.example"])
    def test_credentials_origin_suffix_and_port_tricks_are_rejected(self):
        urls = ["https://approved.example.attacker.test", "https://approved.example:444/path",
                "http://approved.example", "https://user:pass@approved.example/path",
                "https://@approved.example/path", "https://approved.example/path#fragment",
                "file:///etc/passwd", "https://approved.example\\@attacker.test",
                "https://approved.example\n.attacker.test", "https://approved.example%2f.attacker.test"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url("https://approved.example/export?token=value"),
                         "https://approved.example/export?token=value")

    def test_github_static_origin_works_without_custom_allowlist(self):
        adapter = GitHubAdapter({"owner": "owner", "repo": "repo", "token": "secret"})
        response = Mock(status_code=200)
        response.json.return_value = []
        with patch("adapters.http.requests.request", return_value=response) as request:
            self.assertEqual(adapter.get_tasks(), [])
        self.assertEqual(request.call_args.args[1], "https://api.github.com/repos/owner/repo/issues")
        self.assertFalse(request.call_args.kwargs["allow_redirects"])
        with self.assertRaises(ValueError):
            github_http.get("https://attacker.example")

    @override_settings(ADAPTER_ALLOWED_ORIGINS=["https://approved.example"])
    def test_redirects_never_forward_api_keys(self):
        for code in (301, 302, 307, 308):
            response = Mock(status_code=code, headers={"Location": "http://169.254.169.254"})
            with self.subTest(code=code), patch("adapters.http.requests.request", return_value=response) as request:
                with self.assertRaises(HTTPError):
                    adapter_http.post("https://approved.example/api", headers={"x-api-key": "secret"})
                request.assert_called_once()
                self.assertFalse(request.call_args.kwargs["allow_redirects"])
                response.close.assert_called_once()

    def test_policy_is_checked_again_at_request_time(self):
        with override_settings(ADAPTER_ALLOWED_ORIGINS=["https://approved.example"]):
            adapter = GrocyAdapter({"api_url": "https://approved.example", "api_key": "key"})
        with patch("adapters.http.requests.request") as request, self.assertRaises(ValueError):
            adapter._get("/api/chores")
        request.assert_not_called()

    def test_local_exports_are_denied_by_default(self):
        with self.assertRaises(ValueError):
            SuperProductivityAdapter({"sync_file_path": "/etc/passwd"})

    def test_exact_file_allowlist_rejects_other_files_and_symlink_escape(self):
        with TemporaryDirectory() as temp_dir:
            approved = Path(temp_dir) / "export.json"
            private = Path(temp_dir) / "private.json"
            approved.write_text('{"task": {"entities": {}}}')
            private.write_text('{"secret": "private"}')
            link = Path(temp_dir) / "link.json"
            link.symlink_to(private)
            with override_settings(ADAPTER_ALLOWED_FILES=[str(approved)]):
                self.assertEqual(validate_file(str(approved)), approved)
                self.assertEqual(SuperProductivityAdapter({"sync_file_path": str(approved)}).get_tasks(), [])
                for path in (str(private), str(link), "relative.json"):
                    with self.subTest(path=path), self.assertRaises(ValueError):
                        validate_file(path)
