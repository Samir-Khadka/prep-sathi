"""Automated Writing feedback for PrepSathi (Phase 3, backend only).

Guidance only, never an examiner's score. :func:`analyse_writing` reads a
learner's text for one writing prompt and returns a band *range* per
IELTS criterion plus short, actionable notes. Every band shown by the
product carries the "practice estimate, not an official score" label.

What this module can and cannot do
-----------------------------------
It measures only signals that are directly countable in the text:

* **Task achievement** — word count against the prompt minimum, how many
  of the prompt's key content words the text uses, and whether the
  expected structure signal is present (an overview sentence for
  Academic Task 1, a greeting + purpose for a General Task 1 letter,
  a clear position for Task 2).
* **Coherence and cohesion** — paragraph breaks and balance, the number
  of *different* linking words used, and whether the opening sentences
  pick up words from the prompt.
* **Lexical resource** — type-token ratio (different words / all words),
  hits against a fixed academic wordlist, overuse of one non-topic word,
  and how often content-word pairs (bigrams) repeat.
* **Grammatical range and accuracy** — sentence count and length variety
  (standard deviation of sentence lengths), distinct subordinating and
  relative words (although, because, while, which, ...) plus participial
  -ing clauses, and four error patterns that can actually be detected
  mechanically: sentences over 45 words, sentences with no detectable
  verb, "very" used three or more times, and three or more sentences
  opening with "I think".

It cannot judge ideas, argument quality, factual accuracy, or whether
an answer is really on topic the way a human examiner can, and it never
promises a band or an outcome. The ``limits`` field in every response
says this plainly. In particular it does *not* claim to detect
article errors ("a" vs "an"), spelling, punctuation, or agreement
errors — those need a real grammar checker or a human reader.

Calibration
-----------
Thresholds were set from the product's own reference texts, not from
vibes: the 30 model answers in ``content/writing_prompts.json`` score
an overall low end of 7.0 or above, and a weak fixture (about 120
words, one paragraph, repetitive vocabulary) scores an overall high
end of 5.5 or below. See ``docs/phase3-feedback-notes.md`` for the
numbers and ``backend/tests/test_feedback.py`` for the pinned checks.
"""
from __future__ import annotations

import math
import re
import statistics
from collections import Counter

from pydantic import BaseModel, Field

from .scoring import BAND_LABEL

# ---------------------------------------------------------------------------
# Limits statement — returned with every analysis. Keep this wording honest:
# automated feedback is guidance, not an examiner's judgement.
# ---------------------------------------------------------------------------

LIMITS = (
    "Automated feedback only. It counts measurable patterns in your text "
    "(length, linking words, vocabulary variety, sentence variety) and "
    "cannot judge your ideas, the quality of your arguments, or factual "
    "accuracy the way a human examiner can. The band range is guidance "
    "for practice only — it never promises a band or an outcome in a "
    "real test."
)

MIN_BAND = 4.0
MAX_BAND = 8.0

# ---------------------------------------------------------------------------
# Tokenising helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Function words and instruction words. Prompt key words are the prompt's
# words minus these; learner-text stopwords use the same set.
_STOPWORDS = frozenset(
    """
    a an the and or but if then else when while as of at by for with about
    into through after over between out against during without before under
    around among within upon per via
    i me my we our you your he him his she her it its they them their this
    that these those am is are was were be been being have has had do does
    did will would shall should can could may might must
    there here what which who whom whose how why where when
    not no yes so very just also than too only own same such more most other
    some any all each both few much many little own
    in on to from of
    summarise summarize summarised summarise summarising information selecting
    reporting features comparisons relevant discuss views opinion reasons
    answer include examples knowledge experience write least words chart
    table diagram graph below shows show data process letter dear sir madam
    yours faithfully sincerely
    """.split()
)

# Linking devices counted for coherence. Multi-word phrases first so the
# longest match wins when scanning.
LINKERS = [
    "on the other hand",
    "on the one hand",
    "as a result",
    "for example",
    "for instance",
    "in addition",
    "in conclusion",
    "in contrast",
    "in comparison",
    "in general",
    "in my opinion",
    "in my view",
    "in other words",
    "in particular",
    "in summary",
    "in fact",
    "to sum up",
    "to conclude",
    "first of all",
    "compared with",
    "after that",
    "afterwards",
    "on balance",
    "furthermore",
    "moreover",
    "however",
    "therefore",
    "consequently",
    "meanwhile",
    "whereas",
    "nevertheless",
    "nonetheless",
    "similarly",
    "likewise",
    "instead",
    "otherwise",
    "indeed",
    "firstly",
    "secondly",
    "thirdly",
    "finally",
    "lastly",
    "overall",
    "while",
    "also",
    "but",
    "then",
    "next",
    "first",
    "second",
    "third",
]

# Words that mark a complex sentence: subordinating conjunctions and
# relative pronouns, as whole phrases. "that" and "as" are left out —
# they are so common they stop discriminating between simple and
# complex writing. A word may also appear in LINKERS (e.g. "while");
# the two criteria measure different things.
SUBORDINATORS = [
    "as soon as",
    "even though",
    "in order to",
    "so that",
    "although",
    "because",
    "whereas",
    "unless",
    "despite",
    "though",
    "which",
    "whose",
    "whom",
    "before",
    "after",
    "until",
    "while",
    "when",
    "since",
    "once",
    "who",
    "if",
]

# -ing words that are nouns, not participles — excluded when counting
# participial clauses ("in the morning" is not a complex sentence).
_ING_NOUNS = frozenset(
    """
    morning evening wedding building meeting feeling meaning learning
    training reading writing living thing something anything nothing
    during spring king ring sing bring
    """.split()
)

# ~75 formal/academic words, plus formal letter words (grateful,
# concerned, ...) — a letter shows lexical range with formal
# vocabulary, not with data-description words. Linking adverbs are
# deliberately excluded — they are counted under coherence, not here.
ACADEMIC_WORDS = frozenset(
    """
    significant significantly substantial considerably considerable
    consequence consequences implication implications phenomenon
    fundamental crucial essential apparent evident inevitable ultimately
    primarily predominantly approximately proportion trend tendency
    demonstrate illustrate highlight emphasise emphasize contribute
    derive indicate facilitate implement establish maintain fluctuate
    dramatic dramatically gradual widespread complex challenging
    beneficial detrimental feasible sustainable sustainability efficient
    effective accessible affordable perspective approach factor impact
    influence outcome remarkable notable modest modestly sharply
    equality merit participation investment contribution reasonable
    financial society benefit benefits workforce standards critics
    compromise access afford
    grateful appreciate concerned request arrange inconvenience
    assistance regarding delighted unfortunately suitable appropriate
    available responsible reliable experienced qualified occasion
    celebration
    """.split()
)

# Overview / position signals, checked per task type.
OVERVIEW_PHRASES = (
    "overall",
    "in general",
    "it is clear",
    "the chart shows",
    "the table shows",
    "the diagram shows",
    "the graph shows",
    "in summary",
    "the main trend",
    "main features",
    "in conclusion",
)
LETTER_PURPOSE_PHRASES = (
    "i am writing",
)
POSITION_PHRASES = (
    "in my opinion",
    "i believe",
    "i think",
    "in my view",
    "i agree",
    "i disagree",
    "my opinion is",
    "i would argue",
    "personally",
    "in conclusion",
    "overall, i",
)

# Verb detection: auxiliaries, common irregular forms, and a stem list of
# frequent verbs. A sentence "has a verb" if any token is an auxiliary,
# an irregular form, or stems to a verb in the list.
_AUXILIARIES = frozenset(
    """
    am is are was were been being have has had do does did
    will would shall should can could may might must
    """.split()
)
_IRREGULAR_VERBS = frozenset(
    """
    went took made gave saw came knew got found thought said told became
    began brought bought caught chose drew drank drove ate fell felt flew
    forgot grew heard held kept left lost met paid ran read rode rose
    sold sent shook slept spoke spent stood stole swam taught tore woke
    wore won wrote built cut hit put set shut cost hit let shut
    arose awoke borne beaten bitten blown broken chosen driven eaten
    fallen forgotten frozen given hidden ridden risen shaken stolen
    taken torn woken worn written
    """.split()
)
_VERB_STEMS = frozenset(
    """
    show compare increase decrease rise fall grow change become make take
    give help allow lead cause improve reduce provide support believe
    think argue suggest claim agree disagree visit spend live work study
    learn use need want like enjoy prefer play watch read write speak
    travel move pay cost buy sell build create develop produce offer
    receive happen occur exist remain continue begin start finish try
    seem appear feel mean include involve require depend focus discuss
    examine consider address affect benefit damage protect prevent solve
    face experience choose decide expect hope plan aim tend result
    reflect indicate demonstrate reveal attract consist contain feature
    double exceed account amount average total drop climb peak vary
    fluctuate stable steady shrink expand decline surge plunge recover
    listen notice obtain open pass pick practice prevent raise realise
    realize regard return save send share spend stay stop talk teach
    thank wait walk wish worry attract consist contain depend exist
    participate perform prepare present protect reach recognise recognize
    remember remove report represent serve share succeed suffer support
    treat turn understand value visit watch worry compare attract
    damage encourage identify ignore intend join manage perform present
    produce protect realise receive recognise remove require resolve
    respond return reveal review rise risk save serve settle share show
    sign speak spend stand start state stop study suggest support
    survive take talk teach tell tend thank think throw touch trade
    train travel treat try turn understand use visit wait walk want
    watch wear win wish work worry write
    """.split()
)


def _tokens(text: str) -> list[str]:
    """Lowercase alphabetic tokens (apostrophes kept inside words)."""
    return _WORD_RE.findall(text.lower())


def _sentences(text: str) -> list[str]:
    """Split on sentence-final punctuation; drop empty fragments."""
    parts = _SENTENCE_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _paragraphs(text: str) -> list[str]:
    """Blank-line-separated blocks; a text with no blank lines is one."""
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def _round_half(value: float) -> float:
    """Round to the nearest 0.5."""
    return round(value * 2) / 2


def _clamp_band(value: float) -> float:
    return max(MIN_BAND, min(MAX_BAND, _round_half(value)))


def _score_to_band(score_10: float) -> float:
    """Map a 0–10 criterion score to a band centre in 0.5 steps."""
    if score_10 >= 9.0:
        return 8.0
    if score_10 >= 8.0:
        return 7.5
    if score_10 >= 7.0:
        return 7.0
    if score_10 >= 6.0:
        return 6.5
    if score_10 >= 5.0:
        return 6.0
    if score_10 >= 4.0:
        return 5.5
    if score_10 >= 3.0:
        return 5.0
    if score_10 >= 2.0:
        return 4.5
    return 4.0


def _band_range(score_10: float) -> tuple[float, float]:
    """A criterion band range: centre ± 0.5, clamped to 4.0–8.0."""
    centre = _score_to_band(score_10)
    return _clamp_band(centre - 0.5), _clamp_band(centre + 0.5)


def _content_words(text: str) -> list[str]:
    """Non-stopword tokens, in order of appearance."""
    return [w for w in _tokens(text) if w not in _STOPWORDS]


def _prompt_key_words(prompt_text: str) -> list[str]:
    """Distinct content words of the prompt, in first-seen order."""
    seen: list[str] = []
    for word in _content_words(prompt_text):
        if word not in seen:
            seen.append(word)
    return seen


def _has_phrase(text_lower: str, phrases: tuple[str, ...] | list[str]) -> str | None:
    for phrase in phrases:
        if phrase in text_lower:
            return phrase
    return None


def _count_phrase(text_lower: str, phrase: str) -> int:
    return len(re.findall(r"\b" + re.escape(phrase) + r"\b", text_lower))


def _stem(word: str) -> str:
    """Crude suffix strip so 'compares'/'compared'/'comparing' match."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    for suffix in ("ing", "ed", "es"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def _is_prompt_related(word: str, key_words: set[str]) -> bool:
    """True if a word is (a plural/singular form of) a prompt key word —
    repeating the topic words is expected, not a vocabulary weakness."""
    if word in key_words:
        return True
    if word + "s" in key_words:
        return True
    if word.endswith("s") and word[:-1] in key_words:
        return True
    return False


def _sentence_has_verb(sentence: str) -> bool:
    for word in _tokens(sentence):
        if word in _AUXILIARIES or word in _IRREGULAR_VERBS:
            return True
        if _stem(word) in _VERB_STEMS:
            return True
    return False


# ---------------------------------------------------------------------------
# Criterion analysers — each returns (score out of 10, notes)
# ---------------------------------------------------------------------------


def _analyse_task_achievement(
    prompt: dict, text: str, words: list[str], word_count: int
) -> tuple[float, list[str]]:
    min_words = prompt["min_words"]
    ratio = word_count / min_words if min_words else 0.0

    # Length: 4 of 10 points.
    if ratio >= 1.0:
        length_points = 4.0
    elif ratio >= 0.9:
        length_points = 3.5
    elif ratio >= 0.8:
        length_points = 3.0
    elif ratio >= 0.6:
        length_points = 2.0
    elif ratio >= 0.4:
        length_points = 1.0
    else:
        length_points = 0.0

    # Prompt coverage: 3 of 10 points.
    key_words = _prompt_key_words(prompt["prompt"])
    word_set = set(words)
    covered = [w for w in key_words if w in word_set]
    coverage = len(covered) / len(key_words) if key_words else 0.0
    if coverage >= 0.5:
        coverage_points = 3.0
    elif coverage >= 0.35:
        coverage_points = 2.0
    elif coverage >= 0.2:
        coverage_points = 1.0
    else:
        coverage_points = 0.0

    # Expected structure signal: 3 of 10 points.
    lower = text.lower()
    first_sentences = " ".join(_sentences(text)[:3]).lower()
    task = prompt.get("task")
    track = prompt.get("track")
    signal: str | None = None
    if task == 1 and track == "academic":
        signal = _has_phrase(first_sentences, OVERVIEW_PHRASES)
        signal_name = "overview sentence"
    elif task == 1:
        first = first_sentences.lstrip()
        signal = _has_phrase(first_sentences, LETTER_PURPOSE_PHRASES) or (
            "greeting"
            if first.startswith(("dear", "hi ", "hello "))
            else None
        )
        signal_name = "greeting and purpose"
    else:
        signal = _has_phrase(lower, POSITION_PHRASES)
        signal_name = "clear position"
    structure_points = 3.0 if signal else 0.0

    score = length_points + coverage_points + structure_points

    # Under-length caps the score: a short answer cannot score highly on
    # task achievement however well written it is.
    if ratio < 0.5:
        score = min(score, 3.0)
    elif ratio < 0.8:
        score = min(score, 4.0)
    elif ratio < 1.0:
        score = min(score, 5.0)

    notes: list[str] = []
    if ratio >= 1.0:
        notes.append(
            f"Your text has {word_count} words, above the {min_words}-word "
            "minimum — good length for this task."
        )
    else:
        missing = max(0, min_words - word_count)
        notes.append(
            f"Your text has {word_count} words, below the {min_words}-word "
            f"minimum — add about {missing} more words to cover the task fully."
        )
    if key_words:
        shown = ", ".join(covered[:6])
        notes.append(
            f"You covered {len(covered)} of the {len(key_words)} key words "
            f"from the prompt ({shown}) — "
            + (
                "good coverage of the topic."
                if coverage >= 0.35
                else "try to address more of the prompt's key points."
            )
        )
    if signal:
        notes.append(
            f"Your {signal_name} is present ('{signal}') — it tells the "
            "reader what the answer will do."
        )
    else:
        if task == 1 and track == "academic":
            notes.append(
                "Add an overview sentence near the start (for example, "
                "'Overall, ...') that sums up the main trends before the details."
            )
        elif task == 1:
            notes.append(
                "Open with a greeting and a sentence saying why you are "
                "writing (for example, 'I am writing to ...')."
            )
        else:
            notes.append(
                "State your position clearly (for example, 'In my opinion, ...') "
                "so the reader knows where you stand."
            )
    return score, notes


def _analyse_coherence(
    prompt: dict, text: str, words: list[str], sentences: list[str]
) -> tuple[float, list[str]]:
    paras = _paragraphs(text)
    word_count = len(words)
    lower = text.lower()

    # Paragraphs: 3 of 7 points. Model answers in this product are stored
    # as one long block, so a single long paragraph still earns partial
    # credit — the missing breaks are flagged in the notes instead.
    if len(paras) >= 3:
        para_points = 3.0
    elif len(paras) == 2:
        para_points = 2.5
    elif word_count >= 200:
        para_points = 2.5
    elif word_count >= 150:
        para_points = 1.0
    else:
        para_points = 0.0

    # Linking words: 3 of 7 points (distinct devices, not raw count).
    # Task 1 texts are shorter and descriptive, so they are judged
    # against a smaller expected range than Task 2 essays.
    found: dict[str, int] = {}
    for linker in LINKERS:
        count = _count_phrase(lower, linker)
        if count:
            found[linker] = count
    distinct_linkers = len(found)
    if prompt.get("task") == 1:
        if distinct_linkers >= 3:
            linker_points = 3.0
        elif distinct_linkers == 2:
            linker_points = 2.0
        elif distinct_linkers == 1:
            linker_points = 1.0
        else:
            linker_points = 0.0
    else:
        if distinct_linkers >= 5:
            linker_points = 3.0
        elif distinct_linkers >= 3:
            linker_points = 2.0
        elif distinct_linkers >= 1:
            linker_points = 1.0
        else:
            linker_points = 0.0

    # Opening picks up the prompt's words: 1 of 7 points.
    key_words = set(_prompt_key_words(prompt["prompt"]))
    first_para_words = set(_content_words(paras[0])) if paras else set()
    overlap = key_words & first_para_words
    topic_points = 1.0 if len(overlap) >= 2 else 0.0

    points = para_points + linker_points + topic_points

    # Balance penalties (only meaningful with real paragraph breaks).
    one_sentence_paras = sum(
        1 for p in paras if len(_sentences(p)) == 1
    )
    if len(paras) >= 2 and one_sentence_paras:
        points -= 0.5
    if len(paras) >= 2:
        para_word_counts = [len(_tokens(p)) for p in paras]
        if para_word_counts and max(para_word_counts) > 0.75 * word_count:
            points -= 0.5
    most_used = max(found.values()) if found else 0
    if most_used >= 4:
        points -= 0.5
    points = max(0.0, points)

    score = points / 7.0 * 10.0

    notes: list[str] = []
    if len(paras) >= 3:
        notes.append(
            f"Your text is organised into {len(paras)} paragraphs — the "
            "reader can follow the structure."
        )
    elif len(paras) == 2:
        notes.append(
            "Your text has 2 paragraphs — a third paragraph would separate "
            "your ideas more clearly."
        )
    else:
        notes.append(
            "Your text is one long paragraph — split it into 3–4 paragraphs "
            "(introduction, main points, conclusion) so the structure is clear."
        )
    if linker_points >= 3.0:
        shown = ", ".join(sorted(found)[:6])
        notes.append(
            f"You used {distinct_linkers} different linking words ({shown}) "
            "— good range of connections between ideas."
        )
    elif distinct_linkers >= 1:
        shown = ", ".join(sorted(found))
        word = "word" if distinct_linkers == 1 else "words"
        notes.append(
            f"You used {distinct_linkers} different linking {word} ({shown}) — "
            "add more variety, for example 'however', 'in contrast' or "
            "'as a result'."
        )
    else:
        notes.append(
            "You used almost no linking words — connect your ideas with "
            "'however', 'for example', 'as a result' or 'in conclusion'."
        )
    if most_used >= 4:
        repeated = max(found, key=lambda k: found[k])
        notes.append(
            f"You used '{repeated}' {found[repeated]} times — vary it with "
            "other linking words instead of repeating the same one."
        )
    if one_sentence_paras and len(paras) >= 2:
        notes.append(
            "One of your paragraphs is a single sentence — join it to a "
            "neighbouring paragraph or develop the point further."
        )
    if len(overlap) >= 2:
        notes.append(
            "Your opening picks up the prompt's key words, so the reader "
            "knows the answer is on topic."
        )
    else:
        notes.append(
            "Open by naming the topic from the prompt — it shows the answer "
            "is directly on task."
        )
    return score, notes[:4]


def _analyse_lexical(
    prompt: dict, words: list[str], sentences: list[str]
) -> tuple[float, list[str]]:
    word_count = len(words)
    if word_count == 0:
        return 0.0, ["Your text is empty — write something to get feedback."]

    distinct = len(set(words))
    ttr = distinct / word_count

    # Type-token ratio: 3 of 10 points.
    if ttr >= 0.55:
        ttr_points = 3.0
    elif ttr >= 0.50:
        ttr_points = 2.5
    elif ttr >= 0.45:
        ttr_points = 2.0
    elif ttr >= 0.40:
        ttr_points = 1.5
    else:
        ttr_points = 0.5

    # Academic words: 3 of 10 points. Task 1 descriptions and letters
    # legitimately use plainer vocabulary, so the bar is lower than for
    # a Task 2 essay.
    academic_hits = sorted({w for w in set(words) if w in ACADEMIC_WORDS})
    if len(academic_hits) >= 4:
        academic_points = 3.0
    elif len(academic_hits) >= 2:
        academic_points = 2.0
    elif len(academic_hits) == 1:
        academic_points = 1.0
    else:
        academic_points = 0.0

    # Repetition: 2 of 10 points. Prompt key words are excluded (plural-
    # aware) — repeating the topic words is expected, not a weakness.
    key_words = set(_prompt_key_words(prompt["prompt"]))
    content_counts = Counter(
        w
        for w in words
        if w not in _STOPWORDS and not _is_prompt_related(w, key_words)
    )
    top_word, top_count = ("", 0)
    if content_counts:
        top_word, top_count = content_counts.most_common(1)[0]
    if top_count <= 7:
        repeat_points = 2.0
    elif top_count <= 10:
        repeat_points = 1.0
    else:
        repeat_points = 0.0

    # Collocation variety: 2 of 10 points. Distinct content-word bigrams
    # are almost always new, so what is scored is how often a pair is
    # *repeated*: the share of distinct bigrams (built inside sentences)
    # that occur twice or more, ignoring pairs made only of prompt words
    # (data labels legitimately repeat).
    bigram_counts: Counter[tuple[str, str]] = Counter()
    for sentence in sentences:
        content = [w for w in _tokens(sentence) if w not in _STOPWORDS]
        for i in range(len(content) - 1):
            pair = (content[i], content[i + 1])
            if _is_prompt_related(pair[0], key_words) and _is_prompt_related(
                pair[1], key_words
            ):
                continue
            bigram_counts[pair] += 1
    total_bigrams = sum(bigram_counts.values())
    repeated_bigrams = sum(1 for c in bigram_counts.values() if c >= 2)
    if total_bigrams == 0:
        bigram_points = 1.0
        repeated_ratio = 0.0
    else:
        repeated_ratio = repeated_bigrams / total_bigrams
        if repeated_ratio <= 0.03:
            bigram_points = 2.0
        elif repeated_ratio <= 0.06:
            bigram_points = 1.5
        elif repeated_ratio <= 0.10:
            bigram_points = 1.0
        else:
            bigram_points = 0.0

    score = ttr_points + academic_points + repeat_points + bigram_points

    notes: list[str] = []
    notes.append(
        f"Your vocabulary is {'varied' if ttr >= 0.5 else 'quite repetitive'}: "
        f"{distinct} different words in {word_count} "
        f"(type-token ratio {ttr:.2f})."
    )
    if len(academic_hits) >= 4:
        notes.append(
            f"You used {len(academic_hits)} academic words "
            f"({', '.join(academic_hits[:6])}) — good formal vocabulary."
        )
    elif academic_hits:
        notes.append(
            f"You used {len(academic_hits)} academic word(s) "
            f"({', '.join(academic_hits)}) — try more formal words such as "
            "'significant', 'consequence' or 'substantial' where they fit."
        )
    else:
        notes.append(
            "You used no academic words from our list — try formal words "
            "such as 'significant', 'consequence' or 'substantial' where "
            "they fit naturally."
        )
    if top_count > 6 and top_word:
        notes.append(
            f"The word '{top_word}' appears {top_count} times — vary it "
            "with synonyms or rephrase so the vocabulary does not repeat."
        )
    elif repeated_bigrams:
        notes.append(
            f"{repeated_bigrams} of your content-word pairs repeat "
            f"({repeated_ratio:.0%} of all pairs) — vary your word "
            "combinations instead of reusing the same phrases."
        )
    else:
        notes.append(
            f"You used {len(bigram_counts)} different content-word pairs "
            "and almost none repeat — good variety of word combinations."
        )
    return score, notes[:4]


def _analyse_grammar(
    text: str, sentences: list[str]
) -> tuple[float, list[str]]:
    lower = text.lower()
    lengths = [len(_tokens(s)) for s in sentences]
    sentence_count = len(sentences)

    # Sentence-length variety: 3 of 10 points.
    if sentence_count >= 3:
        stdev = statistics.pstdev(lengths)
    else:
        stdev = 0.0
    if stdev >= 6.0:
        variety_points = 3.0
    elif stdev >= 4.0:
        variety_points = 2.5
    elif stdev >= 2.5:
        variety_points = 2.0
    elif stdev >= 1.5:
        variety_points = 1.0
    else:
        variety_points = 0.5

    # Complex-sentence signals: 3 of 10 points. Two countable signals:
    # distinct subordinating/relative words, and sentences with a
    # participial -ing clause (e.g. "attracting 420,000 visitors").
    found_sub: dict[str, int] = {}
    for sub in SUBORDINATORS:
        count = _count_phrase(lower, sub)
        if count:
            found_sub[sub] = count
    distinct_sub = len(found_sub)
    participial = 0
    for sentence in sentences:
        tokens = _tokens(sentence)
        if any(
            w.endswith("ing") and w not in _ING_NOUNS
            for w in tokens[2:]
        ):
            participial += 1
    if distinct_sub >= 4:
        complex_points = 3.0
    elif distinct_sub == 3:
        complex_points = 2.0
    elif distinct_sub == 2:
        complex_points = 1.5
    elif distinct_sub == 1 and participial >= 2:
        complex_points = 1.0
    elif distinct_sub == 1:
        complex_points = 0.5
    elif participial >= 2:
        complex_points = 1.0
    else:
        complex_points = 0.0

    # Detectable error patterns: 4 of 10 points, minus 1 per pattern hit.
    accuracy_points = 4.0
    run_ons = [n for n in lengths if n > 45]
    if run_ons:
        accuracy_points -= 1.0
    no_verb = [
        s for s in sentences if len(_tokens(s)) >= 4 and not _sentence_has_verb(s)
    ]
    if no_verb:
        accuracy_points -= 1.0
    very_count = _count_phrase(lower, "very")
    if very_count >= 3:
        accuracy_points -= 1.0
    i_think_openers = sum(
        1 for s in sentences if s.strip().lower().startswith("i think")
    )
    if i_think_openers >= 3:
        accuracy_points -= 1.0
    accuracy_points = max(0.0, accuracy_points)

    score = variety_points + complex_points + accuracy_points

    notes: list[str] = []
    if sentence_count == 0:
        notes.append("Your text has no complete sentences yet.")
    elif stdev >= 4.0:
        notes.append(
            f"Sentence lengths vary well (from {min(lengths)} to "
            f"{max(lengths)} words) — that reads naturally."
        )
    else:
        notes.append(
            f"Your sentences are mostly the same length "
            f"({min(lengths)}–{max(lengths)} words) — mix short and long "
            "sentences for a more natural rhythm."
        )
    if distinct_sub >= 3:
        shown = ", ".join(sorted(found_sub)[:5])
        notes.append(
            f"You used {distinct_sub} different complex-sentence words "
            f"({shown}) — good range of sentence structures."
        )
    elif distinct_sub >= 1 or participial >= 2:
        shown = ", ".join(sorted(found_sub)[:5]) or "participial -ing clauses"
        notes.append(
            f"You used some complex sentences ({shown}) — add more with "
            "'although', 'because', 'while' or 'which' to join ideas together."
        )
    else:
        notes.append(
            "Try more complex sentences using 'although', 'because', "
            "'while' or 'which' to join ideas together."
        )
    if run_ons:
        notes.append(
            f"One sentence runs to {max(run_ons)} words — split sentences "
            "over 45 words into two shorter ones."
        )
    if no_verb:
        notes.append(
            f"{len(no_verb)} sentence(s) may be missing a main verb — check "
            "each one reads as a complete sentence."
        )
    if very_count >= 3:
        notes.append(
            f"You used 'very' {very_count} times — replace it with a "
            "stronger word ('very big' → 'enormous', 'very important' → "
            "'crucial')."
        )
    if i_think_openers >= 3:
        notes.append(
            f"{i_think_openers} sentences open with 'I think' — vary your "
            "openings ('In my view', 'It seems that', 'One reason is')."
        )
    if not (run_ons or no_verb or very_count >= 3 or i_think_openers >= 3):
        notes.append(
            "No common mechanical issues were found in the patterns this "
            "tool can check — it cannot check spelling or article use, so "
            "proofread those yourself."
        )
    return score, notes[:4]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyse_writing(prompt: dict, text: str) -> dict:
    """Analyse one writing answer and return feedback with a band range.

    ``prompt`` is a writing prompt dict (``id``, ``task``, ``track``,
    ``prompt``, ``min_words``) as stored in ``content/writing_prompts.json``.
    Returns the dict described in the module docstring, with every band
    in 0.5 steps between 4.0 and 8.0 and every note citing what was
    actually measured. Empty text is handled (word count 0, lowest bands)
    rather than raising — the HTTP layer turns empty input into a 400.
    """
    words = _tokens(text)
    word_count = len(words)
    min_words = int(prompt.get("min_words") or 0)
    sentences = _sentences(text)

    ta_score, ta_notes = _analyse_task_achievement(prompt, text, words, word_count)
    cc_score, cc_notes = _analyse_coherence(prompt, text, words, sentences)
    lex_score, lex_notes = _analyse_lexical(prompt, words, sentences)
    gram_score, gram_notes = _analyse_grammar(text, sentences)

    criteria: dict[str, dict] = {}
    for key, score, notes in (
        ("task_achievement", ta_score, ta_notes),
        ("coherence", cc_score, cc_notes),
        ("lexical", lex_score, lex_notes),
        ("grammar", gram_score, gram_notes),
    ):
        low, high = _band_range(score)
        criteria[key] = {"band_low": low, "band_high": high, "notes": notes}

    overall_low = _round_half(
        sum(c["band_low"] for c in criteria.values()) / 4
    )
    overall_high = _round_half(
        sum(c["band_high"] for c in criteria.values()) / 4
    )

    return {
        "prompt_id": prompt.get("id"),
        "word_count": word_count,
        "min_words": min_words,
        "meets_minimum": word_count >= min_words if min_words else False,
        "band_low": overall_low,
        "band_high": overall_high,
        "band_label": BAND_LABEL,
        "criteria": criteria,
        "limits": LIMITS,
    }


# ---------------------------------------------------------------------------
# HTTP models (kept here, not in schemas.py — another agent owns that file)
# ---------------------------------------------------------------------------


class WritingFeedbackRequest(BaseModel):
    prompt_id: str
    # No min_length here: an empty string must reach the endpoint so it can
    # answer 400 (a Pydantic min_length would turn it into a 422).
    text: str = Field(max_length=20000)


class CriterionFeedback(BaseModel):
    band_low: float
    band_high: float
    notes: list[str]


class FeedbackCriteria(BaseModel):
    task_achievement: CriterionFeedback
    coherence: CriterionFeedback
    lexical: CriterionFeedback
    grammar: CriterionFeedback


class WritingFeedbackResponse(BaseModel):
    prompt_id: str
    word_count: int
    min_words: int
    meets_minimum: bool
    band_low: float
    band_high: float
    band_label: str
    criteria: FeedbackCriteria
    limits: str
