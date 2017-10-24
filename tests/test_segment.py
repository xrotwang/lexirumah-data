from unittest import TestCase

from pylexirumah.segment import tokenize_clpa


class Tests(TestCase):
    def test_tokenize_clpa(self):
        self.assertEqual(" ".join([str(x) for x in tokenize_clpa("baa")]), 'b aː')
        with self.assertRaisesRegex(ValueError, "\"9\" is not a valid CLPA segment."):
            " ".join([str(x) for x in tokenize_clpa("a9b", ignore_clpa_errors=False)])

    # TODO: Write more tests.


if __name__ == '__main__':
    unittest.main()
