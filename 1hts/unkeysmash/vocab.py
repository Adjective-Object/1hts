import re, json
import urllib.parse


def sortdict(d):
    return {key: value for key, value in sorted(d.items(), key=lambda item: item[1])}


class Vocab:
    def __init__(self):
        self._words = set()
        self._wordfreq = dict()
        self._total_sample_ct = 0

    def consume_md_str(self, md_str):
        md_clean_words = re.split(
            "\s+",
            re.sub(
                r"([\\\"\[\]\(\)\*_`.,\-/%:&=?~+$!@])",
                " \g<1> ",
                re.sub(
                    r"http[^\s]+\)\]",
                    "",
                    re.sub(
                        r"\]\([^)\s]+\)",
                        "",
                        re.sub(r"\[data:[^]\s]+\]", "", md_str),
                    ),
                ),
            ),
        )
        for word in md_clean_words:
            if not re.match(r".*\d", word) and len(word) >= 3:
                self._words.add(word)
                word_lower = word.lower()
                if word_lower not in self._wordfreq:
                    self._wordfreq[word_lower] = 1
                else:
                    self._wordfreq[word_lower] = self._wordfreq[word_lower] + 1
            else:
                print("omitting", word, "as noise")

        self._update_frequencies()

    def _update_frequencies(self):
        self._total_sample_ct = sum(self._wordfreq.values())
        self._max_sample_ct = max(self._wordfreq.values())
        self._avg_sample_ct = self._total_sample_ct / len(self._wordfreq)

    def dumps(self):
        return json.dumps(
            {
                "_words": list(self._words),
                "_wordfreq": sortdict(self._wordfreq),
            },
            indent=4,
        )

    def loads(dumped_str):
        v = Vocab()
        dumped = json.loads(dumped_str)
        v._wordfreq = dumped["_wordfreq"]
        v._words = set(dumped["_words"])
        v._update_frequencies()
        return v

    def iterwords(self):
        return iter(self._words)

    def relative_frequency(self, word):
        return self._wordfreq[word] / self._max_sample_ct
