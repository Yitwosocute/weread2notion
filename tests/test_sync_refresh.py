import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def install_dependency_stubs():
    notion_client = types.ModuleType("notion_client")
    notion_client.Client = Mock
    notion_errors = types.ModuleType("notion_client.errors")
    notion_errors.APIResponseError = type("APIResponseError", (Exception,), {})
    notion_client.errors = notion_errors

    requests = types.ModuleType("requests")
    requests.Session = Mock

    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None

    retrying = types.ModuleType("retrying")
    retrying.retry = lambda **_kwargs: (lambda function: function)

    sys.modules.setdefault("notion_client", notion_client)
    sys.modules.setdefault("notion_client.errors", notion_errors)
    sys.modules.setdefault("requests", requests)
    sys.modules.setdefault("dotenv", dotenv)
    sys.modules.setdefault("retrying", retrying)


install_dependency_stubs()
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from weread2notion import cli


class SyncRefreshTests(unittest.TestCase):
    def test_old_unfinished_book_refreshes_metadata_without_rebuilding_blocks(self):
        update_existing = Mock()
        insert_new = Mock()

        with (
            patch.object(
                cli,
                "validate_secret_inputs",
                return_value={"notion_token": "token", "weread_api_key": "key"},
            ),
            patch.object(cli, "extract_notion_id", return_value="source-id"),
            patch.object(cli, "Client", return_value=Mock()),
            patch.object(cli, "WeReadGatewayClient", return_value=Mock()),
            patch.object(cli, "resolve_data_source_id", return_value="source-id"),
            patch.object(cli, "load_data_source_schema"),
            patch.object(cli, "get_sort", return_value=100),
            patch.object(
                cli,
                "get_unfinished_page_ids",
                return_value={"book-1": "page-1"},
            ),
            patch.object(
                cli,
                "get_notebooklist",
                return_value=[
                    {
                        "sort": 90,
                        "book": {
                            "bookId": "book-1",
                            "title": "The Story of Philosophy",
                        },
                    }
                ],
            ),
            patch.object(
                cli,
                "update_existing_read_info",
                update_existing,
            ),
            patch.object(cli, "insert_to_notion", insert_new),
            patch("builtins.print"),
        ):
            cli.sync()

        update_existing.assert_called_once_with("page-1", "book-1")
        insert_new.assert_not_called()

    def test_finished_date_is_only_written_when_weread_returns_one(self):
        cli.data_source_property_types = {
            "状态": "status",
            "阅读时长": "rich_text",
            "阅读进度": "number",
            "时间": "date",
        }

        with patch.object(
            cli,
            "get_read_info",
            return_value={
                "markedStatus": 2,
                "readingTime": 60,
                "readingProgress": 0.9,
                "finishedDate": 0,
            },
        ):
            reading = cli.get_read_properties("book-1")

        self.assertEqual("在读", reading["状态"])
        self.assertEqual(0.9, reading["阅读进度"])
        self.assertNotIn("时间", reading)


if __name__ == "__main__":
    unittest.main()
