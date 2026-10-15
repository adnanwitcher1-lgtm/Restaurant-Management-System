from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, F, Max, Sum
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from billing.models import Bill, Payment
from branches.utils import get_current_branch
from inventory.models import InventoryItem
from orders.models import Order, OrderItem

ZERO = Decimal("0")
WEEKDAYS = [(2, "Mon"), (3, "Tue"), (4, "Wed"), (5, "Thu"), (6, "Fri"), (7, "Sat"), (1, "Sun")]


def _parse_date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def _bounds(start, end):
    tz = timezone.get_current_timezone()
    since = timezone.make_aware(datetime.combine(start, time.min), tz)
    until = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
    return since, until


def _totals(branch, since, until):
    agg = Bill.objects.filter(branch=branch, paid_at__gte=since, paid_at__lt=until).aggregate(
        sales=Sum("total"), n=Count("id")
    )
    sales = agg["sales"] or ZERO
    n = agg["n"] or 0
    return sales, n, (sales / n if n else ZERO)


def _delta(cur, prev):
    cur, prev = Decimal(cur or 0), Decimal(prev or 0)
    if prev == 0:
        return None
    pct = (cur - prev) / prev * 100
    return {"value": abs(round(pct, 1)), "up": pct >= 0}


def _hour_label(h):
    return datetime(2000, 1, 1, h).strftime("%I %p").lstrip("0")


@role_required("Owner", "Manager")
def dashboard(request):
    branch = get_current_branch(request)
    today = timezone.localdate()
    start = _parse_date(request.GET.get("from"), today)
    end = _parse_date(request.GET.get("to"), today)
    if start > end:
        start, end = end, start
    if (end - start).days > 365:
        start = end - timedelta(days=365)

    context = {
        "branch": branch,
        "start": start,
        "end": end,
        "today": today,
        "presets": [
            ("Today", today, today),
            ("Yesterday", today - timedelta(days=1), today - timedelta(days=1)),
            ("Last 7 days", today - timedelta(days=6), today),
            ("Last 30 days", today - timedelta(days=29), today),
        ],
    }
    if not branch:
        return render(request, "analytics/dashboard.html", context)

    since, until = _bounds(start, end)
    days = (end - start).days + 1
    prev_since, prev_until = _bounds(start - timedelta(days=days), start - timedelta(days=1))

    sales, count, aov = _totals(branch, since, until)
    p_sales, p_count, p_aov = _totals(branch, prev_since, prev_until)

    bills = Bill.objects.filter(branch=branch, paid_at__gte=since, paid_at__lt=until)

    # Sales by hour (also used for the "busiest hour" insight)
    by_hour = {
        r["h"]: r
        for r in bills.annotate(h=ExtractHour("paid_at"))
        .values("h").annotate(sales=Sum("total"), n=Count("id")).order_by()
    }

    if start == end:
        lo = min([8] + list(by_hour))
        hi = max([22] + list(by_hour))
        labels = [_hour_label(h) for h in range(lo, hi + 1)]
        sales_series = [float(by_hour.get(h, {}).get("sales") or 0) for h in range(lo, hi + 1)]
        orders_series = [by_hour.get(h, {}).get("n", 0) for h in range(lo, hi + 1)]
        if start == today:
            trend_title = "Daily Sales and Order Trends (Today)"
        else:
            trend_title = f"Daily Sales and Order Trends ({start:%d %b})"
    else:
        by_day = {
            r["d"]: r
            for r in bills.annotate(d=TruncDate("paid_at"))
            .values("d").annotate(sales=Sum("total"), n=Count("id")).order_by()
        }
        dates = [start + timedelta(days=i) for i in range(days)]
        labels = [d.strftime("%d %b") for d in dates]
        sales_series = [float(by_day.get(d, {}).get("sales") or 0) for d in dates]
        orders_series = [by_day.get(d, {}).get("n", 0) for d in dates]
        trend_title = "Daily Sales and Order Trends"

    # Payment methods
    method_names = dict(Payment.METHOD_CHOICES)
    pay_rows = list(
        Payment.objects.filter(bill__branch=branch, created_at__gte=since, created_at__lt=until)
        .values("method").annotate(total=Sum("amount")).order_by("-total")
    )
    pay_labels = [
        "Digital" if r["method"] == "online" else method_names.get(r["method"], r["method"])
        for r in pay_rows
    ]
    pay_values = [float(r["total"]) for r in pay_rows]
    PAY_COLORS = {"Cash": "#2d545e", "Card": "#3f8f9c", "Digital": "#e1b382"}
    pay_colors = [PAY_COLORS.get(l, "#9fb8c0") for l in pay_labels]
    pay_legend = [{"label": l, "color": c} for l, c in zip(pay_labels, pay_colors)]
    # Top selling items
    top_rows = list(
        OrderItem.objects.filter(
            order__branch=branch,
            order__bill__paid_at__gte=since,
            order__bill__paid_at__lt=until,
        )
        .values("name").annotate(qty=Sum("quantity"), image=Max("menu_item__image"))
        .order_by("-qty", "name")[:6]
    )
    top_items = [
        {
            "name": r["name"],
            "qty": r["qty"],
            "image": (settings.MEDIA_URL + r["image"]) if r["image"] else "",
        }
        for r in top_rows
    ]
    popular_sold = sum(r["qty"] for r in top_rows[:5])

    # Hourly order density (weekday x hour)
    grid = {}
    for r in (
        Order.objects.filter(branch=branch, created_at__gte=since, created_at__lt=until)
        .exclude(status=Order.CANCELLED)
        .annotate(d=ExtractWeekDay("created_at"), h=ExtractHour("created_at"))
        .values("d", "h").annotate(n=Count("id")).order_by()
    ):
        grid[(r["d"], r["h"])] = r["n"]
    peak = max(grid.values(), default=0)
    used = [h for _, h in grid]
    hours = list(range(min([10] + used), max([22] + used) + 1))
    heat_rows = []
    for d, label in WEEKDAYS:
        cells = []
        for h in hours:
            n = grid.get((d, h), 0)
            alpha = 0.25 + 0.75 * n / peak if n and peak else 0.10
            cells.append({"h": h, "n": n, "alpha": f"{alpha:.2f}"})
        heat_rows.append({"label": label, "cells": cells})
    heat_header = [str(h) for h in hours]
    heat_cols = len(hours)

    # Inventory alerts
    alerts = list(
        InventoryItem.objects.filter(
            branch=branch, is_active=True, quantity__lte=F("low_stock_level")
        ).order_by("quantity")[:12]
    )

    # Insights
    insights = []
    if count:
        best_h = max(by_hour, key=lambda h: by_hour[h]["sales"] or 0)
        insights.append(f"Busiest hour: {_hour_label(best_h)} (Rs. {by_hour[best_h]['sales']:.0f}).")
        if top_items:
            insights.append(f"Best seller: {top_items[0]['name']} ({top_items[0]['qty']} sold).")
        if pay_labels:
            insights.append(f"Most used payment: {pay_labels[0]}.")
    else:
        insights.append("No paid bills in this period yet.")
    if alerts:
        insights.append(f"{len(alerts)} inventory item(s) need restocking.")

    context.update(
        {
            "sales": sales,
            "count": count,
            "aov": aov,
            "popular_sold": popular_sold,
            "d_sales": _delta(sales, p_sales),
            "d_count": _delta(count, p_count),
            "d_aov": _delta(aov, p_aov),
            "trend_title": trend_title,
            "top_items": top_items,
            "heat_rows": heat_rows,
            "heat_header": heat_header,
            "heat_cols": heat_cols,
            "alerts": alerts,
            "insights": insights,
            "has_payments": bool(pay_values),
            "pay_legend": pay_legend,
            "chart": {
                "pay_colors": pay_colors,
                "labels": labels,
                "sales": sales_series,
                "orders": orders_series,
                "pay_labels": pay_labels,
                "pay_values": pay_values,
                "top": top_items,
            },
        }
    )
    return render(request, "analytics/dashboard.html", context)