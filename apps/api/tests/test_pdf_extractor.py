import fitz

from evidence_parse.extractors.pdf import PdfTextExtractor, locate_text


def _pdf_with_separate_lines() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Unit Price: 200.00")
    page.insert_text((72, 96), "Subtotal: 200.00")
    content = document.tobytes(no_new_id=True)
    document.close()
    return content


def test_pdf_text_spans_retain_line_level_evidence() -> None:
    extraction = PdfTextExtractor().extract(_pdf_with_separate_lines())

    subtotal = locate_text("Subtotal: 200.00", extraction.spans)

    assert subtotal.text == "Subtotal: 200.00"
    assert subtotal.page == 1
    assert subtotal.bbox.y0 > extraction.spans[0].bbox.y0
