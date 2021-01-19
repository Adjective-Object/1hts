from .edit_sequences import get_edit_sequences


class Suggester:
    def __init__(self, vocab, edit_sequence_config):
        self.vocab = vocab
        self.edit_sequence_config = edit_sequence_config

    def full_word_match_distance(self, target_word, word_prefix):
        """
        Match words based on a full word

        meant for use in typebehind corrections
        """
        edit_sequence_candidates = get_edit_sequences(
            target_word, word_prefix, self.edit_sequence_config
        )
        if len(edit_sequence_candidates) != 0:
            edit_sequence_score = 100 + min(
                self.edit_sequence_config.scoring_algorithm(edit_sequence)
                for edit_sequence in edit_sequence_candidates
            )
        else:
            # TODO better handle for no available edit sequences
            edit_sequence_score = 200
        word_frequency_component = 1 - self.vocab.relative_frequency(
            target_word.lower()
        )

        return edit_sequence_score * word_frequency_component

    def prefix_match_distance(self, target_word, word_prefix):
        """
        Match words based on the first segment of a word rather than
        the full word

        meant for use in typeahead suggestions
        """
        edit_sequence_candidates = get_edit_sequences(
            target_word[: len(word_prefix)], word_prefix, self.edit_sequence_config
        )
        if len(edit_sequence_candidates) != 0:
            edit_sequence_score = 100 + min(
                self.edit_sequence_config.scoring_algorithm(edit_sequence)
                for edit_sequence in edit_sequence_candidates
            )
        else:
            # TODO better handle for no available edit sequences
            edit_sequence_score = 200
        word_frequency_component = 1 - self.vocab.relative_frequency(
            target_word.lower()
        )

        return edit_sequence_score * word_frequency_component

    def get_prefix_suggestions(self, word_prefix):
        return list(
            sorted(
                # todo keysmash & repetition
                [w for w in self.vocab.iterwords() if word_prefix in w],
                key=lambda w: self.prefix_match_distance(
                    w.lower(), word_prefix.lower()
                ),
                reverse=False,
            )[0:5]
        )
