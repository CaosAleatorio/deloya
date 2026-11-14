"""Private order documents generated from purchase snapshots, never bank receipts."""
from html import escape
from io import BytesIO
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.presentation import money


MAPUTO = ZoneInfo("Africa/Maputo")
PAID_STATES = {"paga", "em_preparacao", "pronta", "entregue"}
STATES = {"pendente_pagamento": "Pendente de pagamento", "paga": "Paga",
          "em_preparacao": "Em preparação", "pronta": "Pronta",
          "entregue": "Entregue", "cancelada": "Cancelada"}


def receipt_content(order):
    """Separate semantic content so payment wording can be tested independently of PDF encoding."""
    settled = order.status in PAID_STATES
    return {
        "title": "REGISTO DE TESTE" if order.is_demo else "Registo da encomenda",
        "demo_notice": "PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO" if order.is_demo else None,
        "warning": "NÃO CONSTITUI PROVA DE DINHEIRO RECEBIDO",
        "payment_note": (
            "O estado apresentado resulta de um pagamento de teste. Não houve movimentação de dinheiro."
            if settled and order.is_demo else
            "Registo informativo do sistema; não substitui factura ou recibo fiscal."
            if settled else
            "Esta encomenda não tem pagamento confirmado. Este registo não é um comprovativo de pagamento."
        ),
        "reference": order.reference,
        "created_at": order.created_at.astimezone(MAPUTO).strftime("%d/%m/%Y %H:%M"),
        "status": STATES.get(order.status, order.status),
        "delivery_method": "Levantamento na loja" if order.delivery_method == "pickup" else "Entrega combinada",
        "address": order.address,
        "notes": order.notes,
        "requested_date": order.requested_date.astimezone(MAPUTO).strftime("%d/%m/%Y %H:%M") if order.requested_date else None,
        "total": money(order.total),
        "stores": [{
            "name": vendor.store.name,
            "status": STATES.get(vendor.status, vendor.status),
            "delivery_fee": money(vendor.delivery_fee),
            "total": money(vendor.total),
            "items": [{"name": item.name, "quantity": item.quantity,
                       "unit_price": money(item.unit_price), "total": money(item.total)}
                      for item in vendor.items],
        } for vendor in order.vendor_orders],
    }


def build_order_receipt(order):
    data = receipt_content(order)
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, title=f"Deloya — {data['title']}",
                                 leftMargin=32, rightMargin=32, topMargin=32, bottomMargin=38)
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12

    def paragraph(value, style="BodyText"):
        return Paragraph(escape(str(value)), styles[style])

    story = [paragraph("Deloya Marketplace", "Title"), paragraph(data["title"], "Heading1")]
    if data["demo_notice"]:
        story.append(paragraph(data["demo_notice"], "Heading2"))
    story.extend([paragraph(data["warning"], "Heading3"), paragraph(data["payment_note"]), Spacer(1, 12)])
    for label, key in [("Referência", "reference"), ("Data (Africa/Maputo)", "created_at"),
                       ("Estado", "status"), ("Recepção", "delivery_method"), ("Morada", "address"),
                       ("Data pretendida, sujeita a confirmação", "requested_date"), ("Notas", "notes")]:
        if data[key]:
            story.append(paragraph(f"{label}: {data[key]}"))
    for store in data["stores"]:
        story.extend([Spacer(1, 14), paragraph(store["name"], "Heading2"),
                      paragraph(f"Estado da subencomenda: {store['status']}")])
        rows = [["Descrição", "Quantidade", "Preço MT", "Total MT"]]
        for item in store["items"]:
            rows.append([paragraph(item["name"]), str(item["quantity"]), item["unit_price"], item["total"]])
        rows.extend([["Entrega", "", "", store["delivery_fee"]], ["Subtotal da loja", "", "", store["total"]]])
        table = Table(rows, repeatRows=1, hAlign="LEFT",
                      colWidths=[document.width * fraction for fraction in (0.52, 0.15, 0.16, 0.17)])
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123d32")),
                                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6dfda")),
                                  ("TOPPADDING", (0, 0), (-1, -1), 6),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(table)
    story.extend([Spacer(1, 14), paragraph(f"Total da encomenda: {data['total']} MZN", "Heading2")])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        text = "REGISTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO" if order.is_demo else "Registo informativo — sem valor fiscal"
        canvas.drawString(doc.leftMargin, 20, text)
        canvas.drawRightString(A4[0] - doc.rightMargin, 20, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
