"""Conservative, explainable clause signals; never legal verdicts."""
import re
from difflib import SequenceMatcher

from .ingest import Section

CATEGORIES = {
    "payment": r"\b(pay|payment|rent|fee|invoice|salary|compensation)\b",
    "termination": r"\b(terminate|termination|end (?:this|the) agreement|cancel)\b",
    "renewal": r"\b(renew|renewal|automatically extend|auto-renew)\b",
    "liability": r"\b(liability|liable|damages|limitation of liability)\b",
    "indemnification": r"\b(indemnif|hold harmless|defend and reimburse)\b",
    "dispute resolution": r"\b(arbitrat|mediat|dispute|venue|jurisdiction)\b",
    "obligation": r"\b(must|shall|required to|agree to|obligated)\b",
    "right": r"\b(may|right to|entitled to|permitted to)\b",
    "penalty": r"\b(penalt|late fee|liquidated damages)\b",
    "confidentiality": r"\b(confidential|non-disclosure|nondisclosure)\b",
}
REVIEW_SIGNALS = [
    (r"\b(automatically renew|auto-renew|automatic renewal)\b", "Automatic renewal may require notice to stop; check the notice window."),
    (r"\b(indemnif|hold harmless)\b", "Indemnification can shift costs or claims between parties."),
    (r"\b(unlimited liability|without limitation|no limit on liability)\b", "The text may leave liability uncapped."),
    (r"\b(arbitrat|waive.{0,25}class action)\b", "Dispute terms may affect where and how a claim is heard."),
    (r"\b(non-compete|noncompete|non-solicit)\b", "Post-relationship restrictions can be important and depend on local law."),
    (r"\b(sole discretion|without notice|at any time for any reason)\b", "One party appears to have broad discretion; read the surrounding terms."),
    (r"\b(late fee|penalty|liquidated damages)\b", "A payment consequence is stated; verify the amount and trigger."),
]
DEADLINE = re.compile(r"\b(?:within\s+)?\d{1,3}\s+(?:calendar\s+|business\s+)?(?:days?|months?|years?)\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:,?\s+\d{4})?\b|\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}\b", re.I)
MONEY = re.compile(r"(?:[$€£]\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:dollars?|euros?|pounds?)\b)", re.I)
PERIOD = re.compile(r"\b\d{1,4}\s+(?:calendar\s+|business\s+)?(?:days?|months?|years?)\b", re.I)


def extract_deadlines(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0) for match in DEADLINE.finditer(text)))


def analyze_chunk(text: str) -> dict:
    categories = [name for name, pattern in CATEGORIES.items() if re.search(pattern, text, re.I)]
    review = [reason for pattern, reason in REVIEW_SIGNALS if re.search(pattern, text, re.I)]
    return {"categories": categories, "review_reasons": review, "deadlines": extract_deadlines(text)}


def changed_terms(before: str, after: str) -> list[dict[str, str]]:
    """Surface exact numerical changes without claiming legal materiality."""
    result = []
    for label, pattern in (("Money amounts", MONEY), ("Time periods", PERIOD)):
        old = list(dict.fromkeys(match.group(0) for match in pattern.finditer(before)))
        new = list(dict.fromkeys(match.group(0) for match in pattern.finditer(after)))
        if old != new and (old or new):
            result.append({"label": label, "before": ", ".join(old) or "Not stated", "after": ", ".join(new) or "Not stated"})
    return result


def compare_chunks(before: list[Section], after: list[Section]) -> list[dict]:
    """Align by heading first, then report content differences without invented materiality."""
    def key(section: Section) -> str:
        return re.sub(r"^(?:section|article|clause)?\s*\d+(?:\.\d+)*[.)]?\s*", "", section.heading.lower()).strip()
    def indexed(sections: list[Section]) -> dict[tuple[str, int], Section]:
        counts: dict[str, int] = {}
        result = {}
        for section in sections:
            name = key(section)
            counts[name] = counts.get(name, 0) + 1
            result[(name, counts[name])] = section
        return result

    left = indexed(before)
    right = indexed(after)
    rows = []
    for name in dict.fromkeys([*left, *right]):
        a, b = left.get(name), right.get(name)
        if a and b:
            if a.text.strip() == b.text.strip():
                continue
            status = "modified"
        else:
            status = "removed" if a else "added"
        rows.append({"heading": (b or a).heading, "status": status, "before": a.text if a else None, "after": b.text if b else None,
                     "changed_terms": changed_terms(a.text if a else "", b.text if b else ""),
                     "similarity": round(SequenceMatcher(None, a.text, b.text).ratio(), 2) if a and b else None})
    return rows
