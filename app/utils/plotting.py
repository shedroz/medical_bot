from __future__ import annotations

from io import BytesIO
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


LOCAL_TZ = datetime.now().astimezone().tzinfo


def _to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def plot_line(points: list[tuple[datetime, float]], title: str, y_label: str) -> BytesIO:
    fig = plt.figure()
    ax = fig.add_subplot(111)

    if not points:
        ax.text(0.5, 0.5, "Нет данных за период", ha="center", va="center")
        ax.set_axis_off()
    else:
        x = [_to_local(dt) for dt, _ in points]
        y = [val for _, val in points]
        ax.plot(x, y, marker="o")
        ax.set_title(title)
        ax.set_xlabel("Дата")
        ax.set_ylabel(y_label)
        fig.autofmt_xdate()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def plot_pressure(points: list[tuple[datetime, int, int]]) -> BytesIO:
    fig = plt.figure()
    ax = fig.add_subplot(111)

    if not points:
        ax.text(0.5, 0.5, "Нет данных за период", ha="center", va="center")
        ax.set_axis_off()
    else:
        x = [_to_local(dt) for dt, _, _ in points]
        sys = [s for _, s, _ in points]
        dia = [d for _, _, d in points]

        ax.plot(x, sys, marker="o", label="SYS")
        ax.plot(x, dia, marker="o", label="DIA")
        ax.set_title("Давление")
        ax.set_xlabel("Дата")
        ax.set_ylabel("мм рт. ст.")
        ax.legend()
        fig.autofmt_xdate()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf