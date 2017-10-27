from unittest import TestCase

from pylexirumah.segment import tokenize_clpa


class Tests(TestCase):
    def test_tokenize_clpa(self):
        self.assertEqual(tokenize_clpa(""), [])
        self.assertEqual(" ".join([str(x) for x in tokenize_clpa("a")]), 'a')
        self.assertEqual(" ".join([str(x) for x in tokenize_clpa("baa")]), 'b aː')

    def test_tokenize_clpa_unknown(self):
        self.assertEqual(" ".join([str(x) for x in tokenize_clpa("ku9")]), 'k u �')

    def test_tokenize_clpa_unknown_exception(self):
        with self.assertRaisesRegex(ValueError, "\"9\" is not a valid CLPA segment."):
            " ".join([str(x) for x in tokenize_clpa("a9b", ignore_clpa_errors=False)])
