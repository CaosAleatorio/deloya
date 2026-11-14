import csv
from datetime import date, datetime, time, timezone
from io import BytesIO, StringIO
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import current_user
from app.database.session import get_db
from app.models import Listing, Order, OrderItem, VendorOrder
from app.services.commerce import approved_store
from app.services.presentation import money

router = APIRouter(prefix="/reports")


MAPUTO = ZoneInfo("Africa/Maputo")


def report_rows(db, user, start, end, status, store_id, is_demo, category_id=None):
    if start and end and start > end:
        raise HTTPException(422, "A data inicial não pode ser posterior à data final")
    if user.role == "admin":
        query = select(VendorOrder).join(Order)
        if store_id:
            query = query.where(VendorOrder.store_id == store_id)
    else:
        store = approved_store(db, user)
        query = select(VendorOrder).join(Order).where(VendorOrder.store_id == store.id)
    if start:
        lower = datetime.combine(start, time.min, tzinfo=MAPUTO).astimezone(timezone.utc)
        query = query.where(Order.created_at >= lower)
    if end:
        upper = datetime.combine(end, time.max, tzinfo=MAPUTO).astimezone(timezone.utc)
        query = query.where(Order.created_at <= upper)
    if status:
        query = query.where(VendorOrder.status == status)
    if is_demo is not None:
        query = query.where(Order.is_demo == is_demo)
    if category_id:
        # EXISTS avoids counting a suborder twice when it contains several matching items.
        matching_item = select(OrderItem.id).join(Listing, OrderItem.listing_id == Listing.id).where(
            OrderItem.vendor_order_id == VendorOrder.id, Listing.category_id == category_id).exists()
        query = query.where(matching_item)
    orders = db.scalars(query.order_by(Order.created_at.desc()).limit(5001)).all()
    if len(orders) > 5000:
        raise HTTPException(422, "Reduza o intervalo do relatório para até 5000 subencomendas")
    return [[v.order.reference, str(v.id), v.store.name,
             v.order.created_at.astimezone(MAPUTO).strftime("%d/%m/%Y"),
             v.status, money(v.total), "TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO" if v.order.is_demo else "REAL"] for v in orders]


def safe_csv(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


@router.get("/orders.csv")
def orders_csv(start: date | None = None, end: date | None = None, status: str | None = None,
               store_id: UUID | None = None, is_demo: bool | None = None, category_id: UUID | None = None,
               user=Depends(current_user), db: Session = Depends(get_db)):
    rows = report_rows(db, user, start, end, status, store_id, is_demo, category_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Encomenda", "Subencomenda", "Loja", "Data (Maputo)", "Estado", "Total MZN", "Modo"])
    writer.writerows([[safe_csv(value) for value in row] for row in rows])
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="deloya-encomendas.csv"', "Cache-Control": "no-store"})


@router.get("/orders.pdf")
def orders_pdf(start: date | None = None, end: date | None = None, status: str | None = None,
               store_id: UUID | None = None, is_demo: bool | None = None, category_id: UUID | None = None,
               user=Depends(current_user), db: Session = Depends(get_db)):
    from html import escape
    rows = report_rows(db, user, start, end, status, store_id, is_demo, category_id)
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), title="Deloya — relatório de encomendas",
                            leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 11
    elements = [Paragraph("Deloya Marketplace — relatório de encomendas", styles["Title"]),
                Paragraph("Os registos identificados como TESTE não constituem prova de dinheiro recebido. "
                          "A moeda é MZN; a data é apresentada no fuso Africa/Maputo.", styles["BodyText"]), Spacer(1, 14)]
    table_rows = [["Encomenda", "Loja", "Data", "Estado", "Total MZN", "Modo"]]
    for row in rows:
        table_rows.append([Paragraph(escape(str(value)), styles["BodyText"]) for value in
                           [row[0], row[2], row[3], row[4], row[5], row[6]]])
    table = Table(table_rows, repeatRows=1, colWidths=[doc.width * weight for weight in (0.17, 0.20, 0.10, 0.14, 0.12, 0.27)])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123d32")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6dfda")),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    elements.append(table)
    doc.build(elements)
    return Response(output.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="deloya-encomendas.pdf"', "Cache-Control": "no-store"})
