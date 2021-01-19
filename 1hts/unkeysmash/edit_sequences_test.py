import unittest
from .edit_sequences import get_edit_sequences


class EditSequencesTest(unittest.TestCase):
    def test_get_edit_sequences_base_merge(self):
        result = get_edit_sequences("abcd", "abcd")
        self.assertEqual(
            result,
            set([(("MAT", "abcd"),)]),
        )

    def test_get_edit_sequences_base_del(self):
        result = get_edit_sequences("abcd", "")
        self.assertEqual(
            result,
            set([(("DEL", "abcd"),)]),
        )

    def test_get_edit_sequences_base_ins(self):
        result = get_edit_sequences("", "abcd")
        self.assertEqual(
            result,
            set([(("INS", "abcd"),)]),
        )

    def test_get_edit_sequences_base_empty(self):
        result = get_edit_sequences("", "")
        self.assertEqual(
            result,
            set([]),
        )

    def add_to_edit_set(self):
        result = add_to_edit_set(
            set(
                [
                    (("SUB", "e", "c"),),
                ]
            ),
            ("MAT", "a"),
        )
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("MAT", "a"),
                        ("SUB", "e", "c"),
                    ),
                ]
            ),
        )

    def test_get_edit_sequences_simple_subst(self):
        result = get_edit_sequences("ae", "ac")
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("MAT", "a"),
                        ("SUB", "e", "c"),
                    ),
                ]
            ),
        )

    def test_get_edit_sequences_end_subst(self):
        result = get_edit_sequences("helo", "helw")
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("MAT", "hel"),
                        ("SUB", "o", "w"),
                    ),
                ]
            ),
        )

    def test_get_edit_sequences_mid_subst(self):
        result = get_edit_sequences("abcd", "ab_d")
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("MAT", "ab"),
                        ("SUB", "c", "_"),
                        ("MAT", "d"),
                    )
                ]
            ),
        )

    def test_get_edit_sequences_beginning_subst(self):
        result = get_edit_sequences("abcd", "~bcd")
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("SUB", "a", "~"),
                        ("MAT", "bcd"),
                    )
                ]
            ),
        )

    def test_get_edit_sequences_beginning_and_middle_subst(self):
        result = get_edit_sequences("abcd", "~b_d")
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("SUB", "a", "~"),
                        ("MAT", "b"),
                        ("SUB", "c", "_"),
                        ("MAT", "d"),
                    ),
                    # (
                    #     ("DEL", "ab"),
                    #     ("SUB", "c", "~"),
                    #     ("INS", "b_"),
                    #     ("MAT", "d"),
                    # ),
                    # (
                    #     ("INS", "~b"),
                    #     ("SUB", "a", "_"),
                    #     ("DEL", "bc"),
                    #     ("MAT", "d"),
                    # ),
                ]
            ),
        )

    def test_get_edit_sequences_med_complex_subst(self):
        result = get_edit_sequences("qw'reall", "we're all")
        self.assertEqual(
            result,
            set(
                [
                    (
                        ("DEL", "q"),
                        ("MAT", "w"),
                        ("INS", "e"),
                        ("MAT", "'re"),
                        ("INS", " "),
                        ("MAT", "a"),
                        ("DEL", "l"),
                        ("MAT", "l"),
                        ("INS", "l"),
                    ),
                    (
                        ("DEL", "q"),
                        ("MAT", "w"),
                        ("INS", "e"),
                        ("MAT", "'re"),
                        ("INS", " "),
                        ("MAT", "a"),
                        ("INS", "l"),
                        ("MAT", "l"),
                        ("DEL", "l"),
                    ),
                    (
                        ("DEL", "q"),
                        ("MAT", "w"),
                        ("INS", "e"),
                        ("MAT", "'re"),
                        ("INS", " "),
                        ("MAT", "all"),
                    ),
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
