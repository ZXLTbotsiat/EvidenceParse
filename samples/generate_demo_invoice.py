"""Generate a synthetic invoice used by the local demo and smoke tests."""

from pathlib import Path

import fitz


OUTPUT = Path(__file__).with_name("demo-invoice.pdf")


def main() -> None:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((56, 70), "NORTHSTAR OFFICE SUPPLIES", fontsize=17)
    page.insert_text((56, 105), "Invoice No: DEMO-2026-0902", fontsize=11)
    page.insert_text((56, 124), "Date: 2026-09-02", fontsize=11)
    page.insert_text((56, 180), "Description          Quantity     Unit Price     Amount", fontsize=10)
    page.insert_text((56, 205), "Document scanner     1            200.00         200.00", fontsize=10)
    page.insert_text((330, 280), "Subtotal: 200.00", fontsize=11)
    page.insert_text((330, 302), "Tax: 36.00", fontsize=11)
    page.insert_text((330, 328), "Total: 236.00", fontsize=13)
    page.insert_text((56, 760), "Synthetic sample - no real customer data", fontsize=8)
    document.save(OUTPUT)


if __name__ == "__main__":
    main()

