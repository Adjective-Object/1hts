import unittest
from .edit_sequences import edit_sequences


class EditSequencesTest(unittest.TestCase):
    def test_edit_sequences_base_merge(self):
        result = edit_sequences("abcd", "abcd")
        self.assertEqual(
            result,
            set([(("MAT", "abcd"),)]),
        )

    def test_edit_sequences_base_del(self):
        result = edit_sequences("abcd", "")
        self.assertEqual(
            result,
            set([(("DEL", "abcd"),)]),
        )

    def test_edit_sequences_base_ins(self):
        result = edit_sequences("", "abcd")
        self.assertEqual(
            result,
            set([(("INS", "abcd"),)]),
        )

    def test_edit_sequences_base_empty(self):
        result = edit_sequences("", "")
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

    def test_edit_sequences_simple_subst(self):
        result = edit_sequences("ae", "ac")
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

    def test_edit_sequences_end_subst(self):
        result = edit_sequences("helo", "helw")
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

    def test_edit_sequences_mid_subst(self):
        result = edit_sequences("abcd", "ab_d")
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

    def test_edit_sequences_beginning_subst(self):
        result = edit_sequences("abcd", "~bcd")
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

    # def test_edit_sequences_beginning_and_middle_subst(self):
    #     result = edit_sequences("abcd", "~b_d")
    #     self.assertEqual(
    #         result,
    #         set(
    #             [
    #                 (
    #                     ("SUB", "a", "~"),
    #                     ("MAT", "b"),
    #                     ("SUB", "c", "_"),
    #                     ("MAT", "d"),
    #                 )
    #             ]
    #         ),
    #     )

    # def test_edit_sequences_med_complex_subst(self):
    #     result = edit_sequences("qw'reall", "we're all")
    #     self.assertEqual(
    #         result,
    #         set([]),
    #     )


if __name__ == "__main__":
    unittest.main()
