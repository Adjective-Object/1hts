# TODO: consider
# spoonerism sequences (DEL x) (MAT y) (INS x) as cheaper
# than a DEL + an INS
#
# scoring SUB based on distance between keys and layer aliasing
#
# scoring INS based on distance between adjacent keys + layer
# aliasing
def default_score_segment(edit_segment):
    seg_class = edit_segment[0]
    if seg_class == "SUB":
        target, source = edit_segment[1], edit_segment[2]
        return len(target)
    else:
        seg_val = edit_segment[1]
        if seg_class == "MAT":
            return -1 * pow(len(seg_class), 2)
        elif seg_class == "DEL":
            return 0.5 + len(seg_class)
        elif seg_class == "INS":
            return len(seg_class)


def default_edit_sequence_score(edit_sequence):
    return sum(default_score_segment(edit_segment) for edit_segment in edit_sequence)


class EditSequencesConfig:
    def __init__(
        self,
        score_diff_cutoff=3,
        walk_diff_cutoff=5,
        scoring_algorithm=default_edit_sequence_score,
    ):
        self.score_diff_cutoff = score_diff_cutoff
        self.walk_diff_cutoff = walk_diff_cutoff
        self.scoring_algorithm = scoring_algorithm


class EditSequenceWalkState:
    def __init__(
        self,
    ):
        self.memo_map = dict()
        self.scores = dict()

    def check_results(self, target, source, target_len, source_len):
        k = (target, source, target_len, source_len)
        if k in self.memo_map:
            return self.memo_map[k]
        else:
            return None

    def set_results(self, target, source, target_len, source_len, results):
        self.memo_map[(target, source, target_len, source_len)] = results


def edit_deletion(seq):
    return ("DEL", seq)


def edit_insertion(seq):
    return ("INS", seq)


def edit_subst(target_seq, source_seq):
    if target_seq == source_seq:
        return edit_match(target_seq)
    else:
        return ("SUB", target_seq, source_seq)


def edit_match(seq):
    return ("MAT", seq)


def merge_same_edit(edit_class, prior, latter):
    if edit_class == "SUB":
        return edit_subst(prior[1] + latter[1], prior[2] + latter[2])
    else:
        return (edit_class, prior[1] + latter[1])


def add_to_edit_set(edit_set, new_suffix_edit):
    next_edit_set = set()
    new_edit_class = new_suffix_edit[0]
    for edit_sequence in edit_set:
        last_edit = edit_sequence[-1]
        last_edit_class = last_edit[0]
        if last_edit_class == "DEL" and new_edit_class == "INS":
            next_edit_set.add(
                edit_sequence[:-1] + (edit_subst(last_edit[1], new_suffix_edit[1]),)
            )
        elif last_edit_class == "INS" and new_edit_class == "DEL":
            next_edit_set.add(
                edit_sequence[:-1] + (edit_subst(new_suffix_edit[1], last_edit[1]),)
            )

        # elif last_edit_class == "SUB" and new_edit_class == "INS":
        #     next_edit_set.add(
        #         edit_sequence[:-1]
        #         + (("SUB", last_edit[1], last_edit[2] + new_suffix_edit[1]),)
        #     )
        # elif (
        #     last_edit_class == "SUB"
        #     and new_edit_class == "DEL"
        #     and last_edit[1].endswith(new_suffix_edit[1])
        # ):
        #     next_edit_set.add(
        #         edit_sequence[:-1]
        #         + (("SUB", last_edit[1], last_edit[2][: -len(new_suffix_edit[1])]),)
        #     )

        else:
            next_edit_set.add(edit_sequence + (new_suffix_edit,))

    return next_edit_set


def concat_consec(seq):
    if len(seq) > 1 and not any([a[0] == b[0] for a, b in zip(seq, seq[1:])]):
        return seq
    else:
        cleanedseq = [seq[0]]

        for t in seq[1:]:
            if t[0] == cleanedseq[-1][0]:
                nextseq = merge_same_edit(
                    t[0],
                    cleanedseq[-1],
                    t,
                )

                cleanedseq.pop()
                cleanedseq.append(nextseq)
            else:
                cleanedseq.append(t)

        return tuple(cleanedseq)


def is_valid_seq(seq):
    for curr in seq:
        curr_edit_class = curr[0]
        if curr_edit_class == "SUB":
            _, target_seq, source_seq = curr
            if source_seq in target_seq or target_seq in source_seq:
                return False
            elif len(source_seq) != len(target_seq):
                return False
            elif len(set(source_seq).intersection(target_seq)) > 0:
                return False

    for prev, curr in zip(seq, seq[1:]):
        prev_edit_class = prev[0]
        curr_edit_class = curr[0]
        if prev_edit_class == "DEL" and curr_edit_class == "INS":
            return False
        elif prev_edit_class == "INS" and curr_edit_class == "DEL":
            return False
        elif curr_edit_class == "SUB":
            _, target_seq, source_seq = curr
            # subbing in the deleted text
            if prev_edit_class == "DEL" and source_seq.startswith(prev[1][0]):
                return False
            # subbing out the inserted text
            elif prev_edit_class == "INS" and target_seq.startswith(prev[1][0]):
                return False
        elif prev_edit_class == "SUB":
            _, prev_target_seq, prev_source_seq = prev
            # subbing in the deleted text
            if curr_edit_class == "INS" and prev_target_seq.endswith(curr[1][-1]):
                return False
            # subbing out the inserted text
            elif curr_edit_class == "DEL" and prev_source_seq.endswith(curr[1][-1]):
                return False

    return True


def _edit_sequences(walk_state, target, source, target_len, source_len, config):
    cached_results = walk_state.check_results(target, source, target_len, source_len)
    if cached_results is not None:
        return cached_results

    # early exit for long sequences to avoid
    # exponential set growth
    if abs(target_len - source_len) > config.walk_diff_cutoff:
        return set()

    # base cases
    if target_len == 0 and source_len == 0:
        return set()
    if target_len == 0:
        return set([(edit_insertion(source[:source_len]),)])
    elif source_len == 0:
        return set(
            [(edit_deletion(target[:target_len]),)],
        )
    elif target[:target_len] == source[:source_len]:
        return set(
            [(edit_match(target[:target_len]),)],
        )

    results = set(
        filter(
            is_valid_seq,
            map(
                concat_consec,
                add_to_edit_set(
                    _edit_sequences(
                        walk_state, target, source, target_len - 1, source_len, config
                    ),
                    edit_deletion(target[target_len - 1]),
                )
                | add_to_edit_set(
                    _edit_sequences(
                        walk_state, target, source, target_len, source_len - 1, config
                    ),
                    edit_insertion(source[source_len - 1]),
                )
                | add_to_edit_set(
                    _edit_sequences(
                        walk_state,
                        target,
                        source,
                        target_len - 1,
                        source_len - 1,
                        config,
                    ),
                    edit_subst(
                        target[target_len - 1],
                        source[source_len - 1],
                    ),
                ),
            ),
        ),
    )

    if config.score_diff_cutoff is not None:
        # filter to best sequences
        scores = dict()
        for res_seq in results:
            if res_seq not in walk_state.scores:
                walk_state.scores[res_seq] = config.scoring_algorithm(res_seq)
            scores[res_seq] = walk_state.scores[res_seq]
        min_score = min(scores.values())
        filtered_results = set(
            filter(
                lambda seq: scores[seq] < min_score + config.score_diff_cutoff, results
            )
        )
        walk_state.set_results(target, source, target_len, source_len, filtered_results)
        return filtered_results
    else:
        walk_state.set_results(target, source, target_len, source_len, results)
        return results


def edit_sequences(target, source, config=EditSequencesConfig()):
    return _edit_sequences(
        EditSequenceWalkState(), target, source, len(target), len(source), config
    )
