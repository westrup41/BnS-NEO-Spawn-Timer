import re
import unicodedata

from rapidfuzz import fuzz


LOOKALIKE = str.maketrans({'а':'a','в':'b','с':'c','е':'e','н':'h','к':'k','м':'m','о':'o','р':'p','т':'t','х':'x','у':'y'})


def clean(value):
    value = unicodedata.normalize('NFKC', str(value)).casefold().replace('ё', 'е')
    return re.sub(r'\s+', ' ', re.sub(r'[^0-9a-zа-я]+', ' ', value)).strip()


def variants(value):
    base = clean(value)
    return list(dict.fromkeys((base, base.translate(LOOKALIKE)))) if base else []


def match_score(phrase, text):
    best = 0
    for phrase_value in variants(phrase):
        for text_value in variants(text):
            if not phrase_value or not text_value: continue
            if re.search(rf'(?<![0-9a-zа-я]){re.escape(phrase_value)}(?![0-9a-zа-я])', text_value): return 100
            if len(phrase_value.replace(' ', '')) < 4: continue
            count = max(1, len(phrase_value.split())); words = text_value.split()
            for candidate in (' '.join(words[index:index + count]) for index in range(len(words))):
                if not candidate: continue
                if min(len(phrase_value), len(candidate)) / max(len(phrase_value), len(candidate)) < 0.70: continue
                best = max(best, int(round(fuzz.ratio(phrase_value, candidate))))
    return best

