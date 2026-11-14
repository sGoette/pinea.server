import re

_WORD_START = re.compile(r"(^|[-(\[])(\w)")

def smart_title(text: str) -> str:
    """Title case for names taken from file and folder names.

    Unlike str.title() it
    - keeps apostrophes intact: "don't look up" -> "Don't Look Up" (not "Don'T Look Up")
    - leaves words that already contain capitals alone: "iPhone", "DVD", "McQueen"
    - capitalizes after hyphens and brackets: "x-men (director's cut)" -> "X-Men (Director's Cut)"
    """
    def fix_word(word: str) -> str:
        if any(char.isupper() for char in word):
            return word
        return _WORD_START.sub(lambda m: m.group(1) + m.group(2).upper(), word)

    return " ".join(fix_word(word) for word in text.split(" "))
