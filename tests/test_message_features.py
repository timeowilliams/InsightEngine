from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_message_features import classify_question_type, extract_message_features


class MessageFeatureTests(unittest.TestCase):
    def test_extracts_linguistic_features(self) -> None:
        feature = extract_message_features(
            {
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "parent_id": None,
                "role": "user",
                "create_time": "2026-01-15T10:00:00+00:00",
                "content_type": "text",
                "text_sha256": "abc",
                "text": "Maybe this is broken? Because the error says no.\n```py\nx = 1\n```",
                "word_count": 11,
                "char_count": 68,
            }
        )

        self.assertEqual(feature["month"], "2026-01")
        self.assertEqual(feature["question_type"], "debugging")
        self.assertEqual(feature["uncertainty_marker_count"], 1)
        self.assertEqual(feature["reasoning_marker_count"], 1)
        self.assertEqual(feature["question_mark_count"], 1)
        self.assertTrue(feature["has_question_mark"])
        self.assertEqual(feature["code_block_count"], 2)

    def test_classifies_question_types(self) -> None:
        cases = {
            "what is logistic regression?": "factual",
            "help me plan the next milestone": "planning",
            "this traceback is failing, can you debug it?": "debugging",
            "are you sure this makes sense?": "reassurance_seeking",
            "what if we compare these approaches?": "exploratory",
            "i disagree; give me the counterargument": "argumentative",
            "how have i changed my thinking here?": "reflective",
            "can this work?": "general_question",
            "please rewrite this paragraph": "statement_or_instruction",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(classify_question_type(text), expected)


if __name__ == "__main__":
    unittest.main()
