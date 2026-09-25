"""Local lexical vector retrieval and strictly sourced answer orchestration."""
import re
import math
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DISCLAIMER = "Legal information, not legal advice. A licensed professional can assess your situation and local law."
STOP = {"what", "how", "does", "the", "this", "that", "with", "from", "about", "there", "their", "would", "could", "should", "which", "when", "where", "is", "are", "was", "for", "and", "you", "your", "have", "has", "any", "much", "many", "can", "do", "to", "of", "a", "an", "in", "it", "be", "each", "must", "shall"}
NUMERIC_CLAIM = re.compile(r"(?:[$€£]\s?\d+(?:,\d{3})*(?:\.\d+)?|\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}\b|\b\d{1,4}\s+(?:days?|months?|years?)\b|\b\d[\d,.]*\s?(?:dollars?|euros?|pounds?)\b|\b\d[\d,.]*\b)", re.I)
UNSAFE_DIRECTIVE = re.compile(r"\b(?:you (?:must|are legally required to|will win|should definitely|should (?:sign|sue|file|pay|ignore))|sign (?:this|the) (?:document|agreement|contract) (?:now|immediately)|guaranteed to win|(?:this|the) (?:contract|agreement|document) is safe)\b", re.I)
NO_ANSWER = re.compile(r"\b(?:I (?:cannot|can't|could not|couldn't) find|not (?:stated|specified|provided|mentioned) in (?:the|this) document|(?:the|this) document does not (?:state|specify|mention))\b", re.I)


def retrieve(chunks: list[dict], question: str, limit: int = 5) -> list[dict]:
    if not chunks:
        return []
    terms = {w for w in re.findall(r"[a-z]{3,}", question.lower()) if w not in STOP}
    if not terms:
        return []
    candidates = []
    corpus = []
    overlaps = []
    for chunk in chunks:
        passage = f"{chunk['heading']} {chunk['text']}"
        words = set(re.findall(r"[a-z]{3,}", passage.lower()))
        overlap = len(terms & words) / len(terms)
        if overlap:
            candidates.append(chunk)
            corpus.append(passage)
            overlaps.append(overlap)
    if not candidates:
        return []
    try:
        matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=1).fit_transform([*corpus, question])
    except ValueError:
        return []
    similarities = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    ranked = []
    for i, chunk in enumerate(candidates):
        score = float(similarities[i]) + 0.14 * overlaps[i]
        if score >= 0.10:
            ranked.append((score, chunk))
    return [dict(chunk, score=round(score, 3)) for score, chunk in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]


def retrieve_hybrid(chunks: list[dict], question: str, query_vector: list[float] | None,
                    vectors: dict[str, list[float]], limit: int = 5) -> list[dict]:
    """Blend persisted semantic vectors with exact-term evidence and a conservative cutoff."""
    lexical_hits = retrieve(chunks, question, limit=len(chunks))
    lexical = {hit['id']: hit['score'] for hit in lexical_hits}
    if query_vector is None:
        return lexical_hits[:limit]
    query_norm = math.sqrt(sum(value * value for value in query_vector))
    if not query_norm:
        return lexical_hits[:limit]
    ranked = []
    for chunk in chunks:
        vector = vectors.get(chunk['id'])
        if not vector or len(vector) != len(query_vector):
            continue
        vector_norm = math.sqrt(sum(value * value for value in vector))
        semantic = sum(a * b for a, b in zip(query_vector, vector)) / (query_norm * vector_norm) if vector_norm else 0
        lexical_score = lexical.get(chunk['id'], 0)
        if semantic >= 0.35 or lexical_score >= 0.10:
            ranked.append((semantic + min(lexical_score, 1) * 0.35, chunk))
    if not ranked:
        return lexical_hits[:limit]
    return [dict(chunk, score=round(score, 3)) for score, chunk in sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]]


def _citations(chunks: list[dict]) -> list[dict]:
    return [{"id": c["id"], "heading": c["heading"], "page": c.get("page", 1), "quote": c["text"]} for c in chunks]


def grounded_answer(question: str, chunks: list[dict], model_output: dict | None) -> dict[str, Any]:
    if not chunks:
        return {"status": "not_found", "answer": "I couldn't find enough in the selected document to answer that. Try another question or check the original text.", "citations": [], "disclaimer": DISCLAIMER}
    if model_output:
        ids = {str(c["id"]) for c in chunks}
        cited = [str(c) for c in model_output.get("citation_ids", [])]
        answer = model_output.get("answer", "")
        if isinstance(answer, str) and NO_ANSWER.search(answer):
            return {"status": "not_found", "answer": "I couldn't find enough in the selected document to answer that. Check the original text or ask a more specific question.", "citations": [], "disclaimer": DISCLAIMER}
        source = " ".join(f"{c['heading']} {c['text']}" for c in chunks if str(c["id"]) in cited)
        claims = {match.group(0).lower().replace(" ", "") for match in NUMERIC_CLAIM.finditer(answer)} if isinstance(answer, str) else set()
        sourced = {match.group(0).lower().replace(" ", "") for match in NUMERIC_CLAIM.finditer(source)}
        short_exact_amount = (isinstance(answer, str) and 2 <= len(answer) < 20 and bool(claims)
                              and answer.strip().rstrip(".").lower() in source.lower())
        if isinstance(answer, str) and (20 <= len(answer) <= 2000 or short_exact_amount) and cited and set(cited) <= ids and claims <= sourced and not UNSAFE_DIRECTIVE.search(answer):
            selected = [c for c in chunks if str(c["id"]) in cited]
            shown_answer = f"The cited passage states: {answer.rstrip('.')}." if short_exact_amount else answer
            return {"status": "answered", "answer": shown_answer, "citations": _citations(selected), "disclaimer": DISCLAIMER}
    return {"status": "source_only", "answer": "I found a relevant passage, shown below. The local AI model is unavailable or could not produce a verifiable answer, so I won't interpret it here.", "citations": _citations(chunks[:2]), "disclaimer": DISCLAIMER}
