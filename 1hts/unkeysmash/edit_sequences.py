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


def _edit_sequences(target, source, target_len, source_len):
    # early exit for long sequences to avoid
    # exponential set growth
    if abs(target_len - source_len) > 5:
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

    return set(
        filter(
            is_valid_seq,
            map(
                concat_consec,
                add_to_edit_set(
                    _edit_sequences(target, source, target_len - 1, source_len),
                    edit_deletion(target[target_len - 1]),
                )
                | add_to_edit_set(
                    _edit_sequences(target, source, target_len, source_len - 1),
                    edit_insertion(source[source_len - 1]),
                )
                | add_to_edit_set(
                    _edit_sequences(target, source, target_len - 1, source_len - 1),
                    edit_subst(
                        target[target_len - 1],
                        source[source_len - 1],
                    ),
                ),
            ),
        )
    )


def edit_sequences(target, source):
    return _edit_sequences(target, source, len(target), len(source))
