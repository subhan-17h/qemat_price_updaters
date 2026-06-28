from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import run_pipeline
import main as price_main
from scripts import send_failure_email


class FakeResponse:
    def __init__(self, payload: bytes = b"{}", status: int = 200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class AutomationTests(unittest.TestCase):
    def test_metadata_validation(self):
        self.assertTrue(
            run_pipeline.metadata_is_new_and_valid(
                {"version": "new", "fileUrl": "https://example.test/bundle", "productCount": 3}, "old"
            )
        )
        self.assertFalse(run_pipeline.metadata_is_new_and_valid({"version": "old"}, "old"))

    @patch("run_pipeline.time.sleep", return_value=None)
    @patch("run_pipeline.get_metadata")
    @patch("run_pipeline.invoke_export")
    def test_export_retries_then_verifies(self, invoke_export, get_metadata, _sleep):
        invoke_export.side_effect = [TimeoutError("network"), None]
        new_metadata = {"version": "new", "fileUrl": "https://example.test/bundle", "productCount": 10}
        get_metadata.return_value = {"version": "old"}
        with patch("run_pipeline.wait_for_metadata_change", return_value=new_metadata):
            result = run_pipeline.export_and_verify("export", "metadata", "old", poll_seconds=0)
        self.assertEqual(result["version"], "new")
        self.assertEqual(invoke_export.call_count, 2)

    @patch("run_pipeline.urlopen")
    def test_fetch_json_performs_json_request(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(b'{"version":"v1"}')
        self.assertEqual(run_pipeline.fetch_json("https://example.test", 1)["version"], "v1")

    def test_pipeline_lock_rejects_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / "pipeline.lock"
            with run_pipeline.pipeline_lock(lock):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with run_pipeline.pipeline_lock(lock):
                        pass

    @patch("run_pipeline.shutil.which", return_value="/usr/bin/tool")
    @patch("run_pipeline.run_command")
    @patch("run_pipeline.get_metadata")
    @patch("run_pipeline.export_and_verify")
    def test_no_change_run_still_exports(self, export, metadata, run_command, _which):
        metadata.return_value = {"version": "old"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "serviceAccountKey.json").write_text("{}")
            products = root / "products.csv"
            products.write_text("product_id,store_id,original_url,price\n1,Metro,url,1\n")
            args = argparse.Namespace(
                products_csv="products.csv", consolidated_csv="consolidated.csv", no_headless=False,
                skip_fetch=True, skip_price_update=False, skip_firebase_update=False,
                skip_bundle_export=False, require_all_stores=True, dry_run=False,
                export_url="export", metadata_url="metadata", lock_file=".pipeline.lock",
            )
            run_pipeline.run_pipeline(args, root)
        commands = [call.args[0] for call in run_command.call_args_list]
        self.assertEqual(len(commands), 1)
        self.assertIn("--require-all-stores", commands[0])
        export.assert_called_once_with("export", "metadata", "old")

    @patch("run_pipeline.shutil.which", return_value="/usr/bin/tool")
    @patch("run_pipeline.run_command", side_effect=__import__("subprocess").CalledProcessError(1, ["python"]))
    @patch("run_pipeline.get_metadata")
    @patch("run_pipeline.export_and_verify")
    def test_scraper_failure_prevents_publish_and_export(self, export, metadata, _run, _which):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "serviceAccountKey.json").write_text("{}")
            (root / "products.csv").write_text("product_id,store_id,original_url,price\n1,Metro,url,1\n")
            args = argparse.Namespace(
                products_csv="products.csv", consolidated_csv="consolidated.csv", no_headless=False,
                skip_fetch=True, skip_price_update=False, skip_firebase_update=False,
                skip_bundle_export=False, require_all_stores=True, dry_run=False,
                export_url="export", metadata_url="metadata", lock_file=".pipeline.lock",
            )
            with self.assertRaises(__import__("subprocess").CalledProcessError):
                run_pipeline.run_pipeline(args, root)
        metadata.assert_not_called()
        export.assert_not_called()

    @patch("run_pipeline.shutil.which", return_value="/usr/bin/tool")
    @patch("run_pipeline.run_command", side_effect=__import__("subprocess").CalledProcessError(1, ["node"]))
    @patch("run_pipeline.get_metadata")
    @patch("run_pipeline.export_and_verify")
    def test_firebase_failure_prevents_export(self, export, metadata, _run, _which):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "serviceAccountKey.json").write_text("{}")
            (root / "consolidated.csv").write_text("product_id,price,price_history\n1,2,[]\n")
            args = argparse.Namespace(
                products_csv="products.csv", consolidated_csv="consolidated.csv", no_headless=False,
                skip_fetch=True, skip_price_update=True, skip_firebase_update=False,
                skip_bundle_export=False, require_all_stores=True, dry_run=False,
                export_url="export", metadata_url="metadata", lock_file=".pipeline.lock",
            )
            with self.assertRaises(__import__("subprocess").CalledProcessError):
                run_pipeline.run_pipeline(args, root)
        metadata.assert_not_called()
        export.assert_not_called()

    @patch("run_pipeline.shutil.which", return_value="/usr/bin/tool")
    def test_firebase_update_precedes_bundle_export(self, _which):
        events = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "serviceAccountKey.json").write_text("{}")
            (root / "consolidated.csv").write_text("product_id,price,price_history\n1,2,[]\n")
            args = argparse.Namespace(
                products_csv="products.csv", consolidated_csv="consolidated.csv", no_headless=False,
                skip_fetch=True, skip_price_update=True, skip_firebase_update=False,
                skip_bundle_export=False, require_all_stores=True, dry_run=False,
                export_url="export", metadata_url="metadata", lock_file=".pipeline.lock",
            )
            with patch("run_pipeline.run_command", side_effect=lambda *_args, **_kwargs: events.append("firebase")), patch(
                "run_pipeline.get_metadata", side_effect=lambda *_args, **_kwargs: events.append("metadata") or {"version": "old"}
            ), patch("run_pipeline.export_and_verify", side_effect=lambda *_args, **_kwargs: events.append("export")):
                run_pipeline.run_pipeline(args, root)
        self.assertEqual(events, ["firebase", "metadata", "export"])

    @patch("main.MultiStoreUpdater")
    def test_require_all_stores_raises_on_store_failure(self, updater_class):
        updater = updater_class.return_value
        updater.results = {
            "Metro": {"products": 10, "comparison_generated": True, "updates_applied": False},
            "Imtiaz": {"products": 10, "comparison_generated": False, "updates_applied": False},
        }
        updater.split_input_csv_by_store.return_value = {"Al-Fatah": 0, "Jalal Sons": 0, "Rainbow": 0, "Metro": 10, "Imtiaz": 10, "Carrefour": 0}
        updater.generate_price_comparisons.return_value = {}
        with self.assertRaisesRegex(RuntimeError, "Imtiaz"):
            price_main.run_price_update_workflow("products.csv", require_all_stores=True)
        updater.update_from_comparisons.assert_not_called()

    @patch("scripts.send_failure_email.recent_journal", return_value="failure details")
    @patch("scripts.send_failure_email.smtplib.SMTP_SSL")
    def test_email_alert_is_rate_limited_and_success_resets_it(self, smtp_ssl, _journal):
        smtp_ssl.return_value.__enter__.return_value = Mock()
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            "os.environ",
            {
                "QEMAT_ALERT_STATE_DIR": temp,
                "SMTP_USERNAME": "subhanamir102@gmail.com",
                "SMTP_APP_PASSWORD": "test-only",
                "ALERT_TO": "subhanamir102@gmail.com",
            },
            clear=False,
        ), patch("scripts.send_failure_email.time.time", return_value=1000):
            self.assertTrue(send_failure_email.send_failure("qemat-test.service"))
            self.assertFalse(send_failure_email.send_failure("qemat-test.service"))
            send_failure_email.mark_success("qemat-test.service")
            self.assertFalse(send_failure_email.state_path("qemat-test.service").exists())
        self.assertEqual(smtp_ssl.call_count, 1)

    @patch("run_pipeline.shutil.which", return_value="/usr/bin/tool")
    @patch("run_pipeline.run_command")
    @patch("run_pipeline.get_metadata")
    @patch("run_pipeline.export_and_verify")
    def test_dry_run_has_no_http_calls(self, export, metadata, _run, _which):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "serviceAccountKey.json").write_text("{}")
            args = argparse.Namespace(
                products_csv="products.csv", consolidated_csv="consolidated.csv", no_headless=False,
                skip_fetch=False, skip_price_update=False, skip_firebase_update=False,
                skip_bundle_export=False, require_all_stores=True, dry_run=True,
                export_url="export", metadata_url="metadata", lock_file=".pipeline.lock",
            )
            run_pipeline.run_pipeline(args, root)
        metadata.assert_not_called()
        export.assert_not_called()


if __name__ == "__main__":
    unittest.main()
