from typing import List, Optional

from evidence_parse.extractors.pdf import TextSpan, locate_text
from evidence_parse.models import Evidence, ExtractedValue

AUTO_ACCEPT_CONFIDENCE = 0.8
TEXT_PATTERN_CONFIDENCE = 0.92
UNLOCATED_PATTERN_CONFIDENCE = 0.75


def extracted_value(
    value: str,
    source_text: str,
    spans: List[TextSpan],
    page: Optional[int] = None,
) -> ExtractedValue:
    """Build a value whose confidence and evidence share one consistent policy."""
    evidence: List[Evidence] = []
    confidence = UNLOCATED_PATTERN_CONFIDENCE
    try:
        source_span = locate_text(source_text, spans, page)
        evidence.append(
            Evidence(
                page=source_span.page,
                text=source_span.text,
                bbox=source_span.bbox,
            )
        )
        confidence = round(TEXT_PATTERN_CONFIDENCE * source_span.confidence, 4)
    except LookupError:
        pass

    review_required = not evidence or confidence < AUTO_ACCEPT_CONFIDENCE
    if not evidence:
        review_reason = "Value matched but source coordinates were not found."
    elif review_required:
        review_reason = "Value confidence is below the automatic acceptance threshold."
    else:
        review_reason = None
    return ExtractedValue(
        value=value.strip(),
        confidence=confidence,
        evidence=evidence,
        review_required=review_required,
        review_reason=review_reason,
    )


def missing_value(name: str) -> ExtractedValue:
    return ExtractedValue(
        confidence=0,
        review_required=True,
        review_reason=f"{name} was not found in the document text.",
    )
