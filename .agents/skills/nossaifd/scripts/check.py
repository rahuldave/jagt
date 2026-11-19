"""Check Markdown prose against the measurable rules in GUIDE.md.

    uv run --no-project python check.py page.md [page.md ...]   report each page; exit 1 if a hard rule is broken, 2 if a page cannot be read
    uv run --no-project python check.py -v page.md              also show the soft notes, for a person to judge

The checks read prose only: paragraphs, list items and headings. Front matter, code blocks, inline code,
tables, link targets, URLs, image lines, HTML and text in straight double quotes are not checked. Markdown comes first,
and quoted words are examples that the text talks about. A program cannot judge meaning, tone or a missing definition, so read the page too.
"""

import re
import sys
from pathlib import Path

SIMPLER = {
    "allow": "let", "allows": "lets", "enable": "let", "enables": "lets", "ensure": "make sure",
    "utilize": "use", "via": "through", "approximately": "about", "provide": "give", "provides": "gives",
    "perform": "do", "launch": "start", "prior": "before", "obtain": "get", "additional": "more",
    "however": "but", "therefore": "so", "whereas": "but", "although": "but", "unless": "if ... not",
    "simply": "(remove)", "just": "(remove)", "really": "(remove)", "actually": "(remove)",
    "basically": "(remove)", "quite": "(remove)", "crucial": "(remove)", "pivotal": "(remove)",
    "robust": "(a fact)", "seamless": "(a fact)", "seamlessly": "(a fact)", "powerful": "(a fact)",
    "delve": "look at", "leverage": "use", "landscape": "(a fact)", "tapestry": "(a fact)",
    "unlock": "(a fact)", "elevate": "(a fact)", "empower": "let", "matters": "(a fact)",
}
ING_OK = {"during", "nothing", "something", "anything", "everything", "thing", "things", "string", "strings",
          "bring", "ring", "spring", "morning", "evening", "heading", "headings", "setting", "settings",
          "warning", "warnings", "padding", "missing", "pending", "ending",
          # Nouns that end in -ing. They name a thing or a field, so they are not verb forms.
          "writing", "meaning", "meanings", "drawing", "drawings", "reading", "feeling", "feelings", "learning",
          "opening", "finding", "findings", "listening", "speaking", "building", "buildings", "training",
          "handwriting", "recording", "recordings", "meeting", "meetings", "spelling", "wording", "timing"}
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being)\s+(\w+ed|made|shown|kept|read|written|run|done|given|taken|"
                     r"seen|set|put|built|sent|found|left|thrown|known|held|drawn|told|hidden)\b", re.I)
COMMAND = re.compile(r"^(add|ask|change|check|choose|click|close|copy|delete|do|give|go|keep|look|make|move|open|"
                     r"press|put|read|remove|restart|run|see|select|send|set|show|start|stop|take|tell|try|type|use|"
                     r"write|edit|install|clone|follow|name|point|rehearse|drag|pass|leave)\b", re.I)
# A count that announces what comes, as in "Three things to know." or "Two cautions:". The noun after the count
# must be one that announces, so that a sentence of fact such as "Two tests timed out." is not a count.
ANNOUNCE = (r"things|ways|points|notes|steps|reasons|tips|questions|cautions|warnings|rules|parts|ideas|facts|"
            r"problems|changes|options|lessons|takeaways|caveats|items|issues|considerations|benefits|goals")
COUNT = re.compile(r"^(two|three|four|five|six|seven|several|a few)\s+(?:\w+\s+)?(?:" + ANNOUNCE + r")(?:\s+to\s+\w+)?[.:]",
                   re.I)
VAGUE = re.compile(r"^(this|that|these|those)\s+(is|was|are|were|means|meant|makes|made|lets|shows|gives|keeps|"
                   r"says|does|did|can|will|would|should|matters|helps)\b", re.I)
# A noun that names an action, followed by "of", as in "a measurement of the latency". Rule 9 of the guide,
# from Rosalind Reid, asks for the verb. Some such nouns name a thing and not an action, so they are left out.
ACTION_NOUN = re.compile(r"\b([A-Za-z]+(?:tion|sion|ment|ance|ence))\s+of\b", re.I)
ACTION_OK = {"action", "section", "version", "question", "position", "function", "condition", "edition", "portion",
             "proportion", "fraction", "nation", "station", "mention", "dimension", "element", "segment",
             "moment", "document", "comment", "environment", "department", "instance", "distance", "sentence",
             "sequence", "audience", "evidence", "importance", "difference", "reference", "experience", "science"}
# A sentence is usually 25 words at most, and an instruction 20. A longer sentence is a soft note, because an
# occasional long sentence is fine when its punctuation makes it clear. Past this limit it is a hard problem.
LONGEST = 40
CLAUSE = re.compile(r",\s+(and|but|so|which|because|while|when|where|if|or)\b|\b(because|which|while|whereas)\b", re.I)


def blocks(text: str) -> list[tuple[int, str, str]]:  # (line, text, kind) with kind "para", "item", "cell" or "head"
    "Read the prose of a page: paragraphs, list items and headings. Code and tables are left out."
    out, block, start, fence, kind = [], [], 0, "", "para"   # fence: the run of ` or ~ that opened the code, or ""

    def flush() -> None:
        nonlocal block
        if block:
            out.append((start, " ".join(block), kind))
        block = []

    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        # Front matter keeps its own syntax: skip it to its closing line, so the line numbers stay the same.
        # Only YAML counts as front matter. A page can also start with a --- rule, and its prose is checked.
        end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
        body = lines[1:end] if end is not None else []
        yaml = re.compile(r"^(?:[A-Za-z0-9_-]+:(?:\s|$)|\s+\S|-\s|#)")
        key = re.compile(r"^[A-Za-z0-9_-]+:(?:\s|$)")
        if end is not None and body and key.match(body[0]) and all(yaml.match(line) for line in body if line.strip()):
            lines[: end + 1] = [""] * (end + 1)
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        mark = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence:
            # As CommonMark: only the same character, at least as many times, with nothing after it, closes the code
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence) and not stripped[len(mark.group(1)):].strip():
                fence = ""
            continue
        if mark:
            fence = mark.group(1)
            flush()
            continue
        if re.match(r"^:::+(\s*[\w{].*)?$", stripped):
            flush()
            continue  # a fenced div, such as ::: do or :::, is markup, as a code fence is
        if not stripped or stripped.startswith("![") or stripped.startswith("<"):
            flush()
            continue
        if stripped.startswith("#"):
            flush()
            out.append((number, stripped.lstrip("#").strip(), "head"))
            continue
        if stripped.startswith("|"):
            flush()
            continue  # tables are exempt: a cell can be a short phrase, a fragment or a value
        item = re.match(r"^\s*(?:[-*+]|\d+\.)\s+(.*)", line)
        if item:
            flush()
            start, kind, block = number, "item", [item.group(1)]
            continue
        if not block:
            start, kind = number, "para"
        block.append(stripped)
    flush()
    return out


def plain(text: str) -> str:  # Prose with inline code as one word, link text kept, markup gone
    "Reduce Markdown inline syntax to plain words."
    text = re.sub(r"`[^`]*`", "CODE", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "URL", text)
    text = re.sub(r'"[^"\n]*"', "QUOTE", text)  # quoted words are examples being talked about, not prose
    return re.sub(r"[*_]", "", text)


def sentences(text: str) -> list[str]:  # The sentences of a block
    "Split after a full stop, question mark or exclamation mark that ends a sentence."
    # A new sentence can start in lower case, as with a name like "timewalk" or "git". The full stops of "e.g."
    # and "i.e." do not end a sentence, so they are hidden while the text is split, and then put back.
    hidden = re.sub(r"\b(?:e\.g|i\.e)\.", lambda m: m.group(0).replace(".", "\0"), text, flags=re.I)
    return [s.strip().replace("\0", ".") for s in re.split(r"(?<=[.!?])\s+(?=[A-Za-z\"(])", hidden) if s.strip()]


def check(path: Path) -> tuple[list[str], list[str]]:  # Hard problems, soft notes
    "Check one page."
    hard, soft = [], []
    for line, raw, kind in blocks(path.read_text(encoding="utf-8")):
        text = plain(raw)
        where = f"{line}"
        for mark, name in (("\u2014", "an em dash"), ("\u2013", "an en dash"), ("\u00b7", "a middle dot"),
                           ("\u201c", "a curly quote"), ("\u201d", "a curly quote"), ("\u2018", "a curly quote"), ("\u2019", "a curly quote")):
            if mark in text:
                hard.append(f"{where}: {name}")
        if kind == "head":
            if COUNT.match(text):
                hard.append(f"{where}: a heading that opens with a count: {text}")
            continue
        found = sentences(text)
        if kind == "para" and len(found) > 6:
            hard.append(f"{where}: a paragraph of {len(found)} sentences (6 at most)")
        if kind in ("para", "item") and found and COUNT.match(found[0]):
            hard.append(f"{where}: opens with a count: {found[0][:60]}")
        questions = 0
        for sentence in found:
            words = re.findall(r"[A-Za-z0-9][\w'\-./]*", sentence)
            limit = 20 if COMMAND.match(sentence) else 25   # usually; an occasional longer sentence is fine
            if len(words) > LONGEST:
                hard.append(f"{where}: {len(words)} words (at most {LONGEST}): {sentence[:80]}")
            elif len(words) > limit:
                soft.append(f"{where}: {len(words)} words (usually at most {limit}): {sentence[:80]}")
            if VAGUE.match(sentence):
                hard.append(f"{where}: a vague demonstrative: {sentence[:60]}")
            # Each colon counts, not only the first. The text before a colon, back to the colon before it,
            # is a short label when it has 3 words or fewer, as in "Note: the parser reads the file."
            start = 0
            for colon in re.finditer(r":(?=\s+\S)", sentence):
                if len(sentence[start:colon.start()].split()) > 3 and kind != "cell":
                    hard.append(f"{where}: a colon between clauses: {sentence[:80]}")
                    break
                start = colon.end()
            if len(CLAUSE.findall(sentence)) >= 2:
                soft.append(f"{where}: maybe three clauses: {sentence[:80]}")
            questions = questions + 1 if sentence.endswith("?") else 0
            if questions == 2:
                soft.append(f"{where}: two questions in a row: answer them, or keep them only to build tension")
        for word in re.findall(r"\b[A-Za-z]+n't\b|\b[A-Za-z]+'(?:re|ll|ve|d|m)\b|\b(?:it|that|there|here|what|who)'s\b", text, re.I):
            hard.append(f"{where}: a contraction: {word}")
        for word in re.findall(r"\b(?:i\.e|etc)\b\.?", text):
            hard.append(f"{where}: say it in words, not {word}")
        if re.search(r"\bnot (just|only)\b", text, re.I):
            hard.append(f"{where}: 'not just' or 'not only': state what the thing is")
        for word in re.findall(r"\b[A-Za-z]+\b", text):
            key = word.lower()
            if key in SIMPLER:
                soft.append(f"{where}: '{word}': try {SIMPLER[key]}")
            if key.endswith("ing") and key not in ING_OK and len(key) > 4 and not (word[0].isupper() and
                                                                                re.search(rf"[a-z,] {word}\b", text)):
                # A capitalized -ing word in the middle of a sentence is part of a name, as in "Communicating Your Work"
                soft.append(f"{where}: an -ing form: {word}")
        for match in ACTION_NOUN.finditer(text):
            before = text[: match.start()].rstrip()
            if match.group(1)[0].isupper() and before and before[-1] not in ".!?:;(":
                continue  # a capital in the middle of a sentence starts a name, as in "Association of"
            if match.group(1).lower() not in ACTION_OK:
                soft.append(f"{where}: maybe an action in a noun, try a verb: {match.group(0)}")
        for match in PASSIVE.finditer(text):
            soft.append(f"{where}: maybe passive: {match.group(0)}")
        if ";" in text:
            soft.append(f"{where}: a semicolon")
    return hard, soft


def main() -> None:
    "Check every page named on the command line. Exit 2 when a page cannot be read, else 1 on a hard problem."
    verbose = "-v" in sys.argv
    failed = unread = False
    for name in (a for a in sys.argv[1:] if a != "-v"):
        try:
            hard, soft = check(Path(name))
        except (OSError, UnicodeDecodeError) as error:
            print(f"{name}: cannot be read: {error.strerror if isinstance(error, OSError) else error}",
                  file=sys.stderr)
            unread = True
            continue
        print(f"{name}: {len(hard)} hard, {len(soft)} soft")
        for problem in hard:
            print("  HARD " + problem)
        if verbose:
            for note in soft:
                print("  soft " + note)
        failed = failed or bool(hard)
    sys.exit(2 if unread else 1 if failed else 0)


if __name__ == "__main__":
    main()
