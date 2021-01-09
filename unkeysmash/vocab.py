import re, json
import urllib.parse


def sortdict(d):
    return {key: value for key, value in sorted(d.items(), key=lambda item: item[1])}


class Vocab:
    def __init__(self):
        self._words = set()
        self._wordfreq = dict()

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
        return v

    def suggestions(self, word_prefix):
        return sorted(
            [w for w in self.words if w in self._words],
            lambda w: self._wordfreq[w.lower()],
        )
