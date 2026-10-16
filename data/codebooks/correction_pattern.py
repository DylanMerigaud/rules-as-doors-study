"""The pinned correction detector of the field study (review round 4, R2-R2-10), as the
extraction ran it: the pattern and the normalisation, verbatim from the repository at commit
af1ceb20, where they were calibrated on 2026-08-29 against 14 days of the operator's own typed
inputs (French and English, his register, profanity included).

How the extraction applied it (data/README.md, `corr_hits_operator_likely`): to the first 400
characters of each operator-likely input (as `human_msgs_operator_likely` defines it: a
main-thread user-role entry with text under the exclusions of `human_msgs`, at most 1,500
characters, not a keepalive, not the first prompt of a popped terminal), after `normalize`. A
hit is a candidate correction; the coders' "corrects a behaviour" code
(data/codebooks/correction_mapping.md, field 1) screened out the hits that correct nothing. Its precision over all its hits is not published: the hits include corrections
of out-of-scope rules, whose count the study does not give.
"""
import re
import unicodedata

CORRECTION_RE = re.compile(
    r"\b(pk (tu|t'|t as|m')|pourquoi (tu|t')|t'as (pas|encore|rien)|tu (as|m'as) pas|"
    r"je t'(ai|avais) (deja )?dit|on avait dit|t'?arrete|wtf|non du tout|tu fumes?|"
    r"c'est pas ce que|pas ce que j'?ai demande|ta merde|putain|putin|bouge le cul|"
    r"encore une fois|toujours pas|fai[st] chier|casse les couilles|n'importe quoi|nimp|"
    r"non pas ca|you did it again|i already told you|not what i asked)\b")


def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace(chr(0x2019), "'")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_candidate(typed):
    """True when the first 400 characters of an operator-likely input match the pattern."""
    return bool(CORRECTION_RE.search(normalize(typed[:400])))
