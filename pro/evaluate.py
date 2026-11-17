"""Scores an extractor against documents whose correct values a professional has labeled.

Today the only labeled set is the synthetic demo documents, which proves the harness runs and nothing about real-world
accuracy. When a firm authorizes de-identified examples, put half in a development set and keep the other half as a
held-out evaluation set that is never used to tune rules or prompts.

A labeled example is: the document's pages, its correct type, and the correct value for each field (None when the
document does not contain that field).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from pro import extract


@dataclass
class Example:
    name: str
    pages: list[extract.PageText]
    doc_type: str
    expected: dict[str, str | None]


@dataclass
class Score:
    documents: int = 0
    type_errors: int = 0
    fields_expected: int = 0
    fields_correct: int = 0
    fields_wrong: int = 0              # extracted a different value than the label
    fields_missed: int = 0             # label has a value, extractor found none
    unsupported: int = 0               # extractor returned a value the label says isn't there
    missing_evidence: int = 0          # a proposal without a page or quoted line
    seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


def score(extractor, examples: list[Example]) -> Score:
    result = Score()
    start = time.perf_counter()
    for ex in examples:
        result.documents += 1
        found = extract.run(extractor, ex.pages)
        if found.doc_type != ex.doc_type:
            result.type_errors += 1
            result.errors.append(f"{ex.name}: type {found.doc_type}, expected {ex.doc_type}")
        values: dict[str, list[str]] = {}
        for p in found.proposals:
            values.setdefault(p.key, []).append(p.value)
            if not p.page or not p.evidence:
                result.missing_evidence += 1
        for key, expected in ex.expected.items():
            got = values.get(key, [])
            if expected is None:
                result.unsupported += len(got)
                continue
            result.fields_expected += 1
            if not got:
                result.fields_missed += 1
                result.errors.append(f"{ex.name}: missed {key}")
            elif any(extract.normalize(v) == extract.normalize(expected) for v in got):
                result.fields_correct += 1
            else:
                result.fields_wrong += 1
                result.errors.append(f"{ex.name}: {key} = {got}, expected {expected}")
    result.seconds = round(time.perf_counter() - start, 4)
    return result
