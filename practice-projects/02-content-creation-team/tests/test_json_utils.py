import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from sop_artifacts import DraftContent  # noqa: E402
from utils.json_utils import parse_llm_json  # noqa: E402


class JsonUtilsTest(unittest.TestCase):
    def test_parse_llm_json_repairs_markdown_invalid_escape(self):
        raw = r'''{
  "title": "测试报告",
  "content_markdown": "# 测试报告\n\n- 优先使用tier\_1来源数据。\n\n## 参考资料\n[1] https://example.com/report",
  "word_count": 3000,
  "citations": [
    "https://example.com/report"
  ]
}'''

        draft = parse_llm_json(raw, DraftContent)

        self.assertIn("tier\\_1", draft.content_markdown)
        self.assertIn("[1] https://example.com/report", draft.content_markdown)
        self.assertEqual(draft.citations, ["https://example.com/report"])


if __name__ == "__main__":
    unittest.main()
