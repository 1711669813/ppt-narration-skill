import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop.pipeline import endpoint, parse_json, validate_cues, generate


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.slide = {"page": 2, "notes": "", "shapes": [
            {"name": "标题", "text": "测试", "rect": [0, 0, 1, .2]},
            {"name": "表格", "text": "数值", "rect": [.2, .3, .8, .9],
             "rows": [[.2, .3, .8, .5], [.2, .5, .8, .9]]}]}

    def test_trusted_geometry_and_intro(self):
        value = {"cues": [{"text": "本页概述。", "mark": "box", "targets": [{"shape": 0}]},
                           {"text": "看第二行。", "mark": "zoom", "targets": [{"shape": 1, "row": 1}]}]}
        cues = validate_cues(value, self.slide)
        self.assertEqual(cues[0]["m"], "none")
        self.assertEqual(cues[1]["r"], [[.2, .5, .8, .9]])
        self.assertEqual(cues[1]["m"], "zoom")
        self.assertTrue(all(c["m"] == "none" for c in validate_cues(value, self.slide, True)))

    def test_invalid_model_output_rejected(self):
        for targets in ([{"shape": -1}], [{"shape": True}], [{"shape": 1, "row": 3}]):
            with self.assertRaises(ValueError):
                validate_cues({"cues": [{"text": "有效句子", "targets": targets}]}, self.slide)
        with self.assertRaises(ValueError):
            validate_cues({"cues": [{"text": "字数超限"}]}, self.slide, max_chars=2)

    def test_https_and_endpoint(self):
        self.assertEqual(endpoint("https://example.com/v1/"), "https://example.com/v1/chat/completions")
        self.assertEqual(endpoint("http://127.0.0.1:8000/v1"), "http://127.0.0.1:8000/v1/chat/completions")
        for url in ("http://example.com", "https://key@example.com/v1", "https://example.com/v1?key=secret"):
            with self.assertRaises(ValueError):
                endpoint(url)

    def test_repair_and_safe_serialization(self):
        text = "__import__('os').system('echo should-not-run')"
        config = {"minutes": 10, "style": "严谨学术汇报", "pptx": "demo.pptx"}
        answer = json.dumps({"title": "测试", "cues": [{"text": text, "mark": "none", "targets": []}]})
        with tempfile.TemporaryDirectory() as folder, patch("desktop.pipeline.chat", side_effect=["invalid", answer]) as call:
            generate(config, [self.slide], Path(folder))
            self.assertEqual(call.call_count, 2)
            # AST literal values confirm that model strings did not become code.
            import ast
            tree = ast.parse((Path(folder) / "cues.py").read_text(encoding="utf-8"))
            values = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body}
            self.assertEqual(values["CUES"][2][0]["t"], text)
        self.assertEqual(parse_json('```json\n{"cues": []}\n```'), {"cues": []})


if __name__ == "__main__":
    unittest.main()
