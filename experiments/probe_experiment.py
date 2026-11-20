"""Measure separate-chaining probe counts over several load factors."""

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable

CAPACITY = 4093
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
FAILED_QUERIES = 4096
RANDOM_SEED = 20261120

OUTPUT_DIR = Path(__file__).resolve().parent
CSV_PATH = OUTPUT_DIR / "results.csv"
SVG_PATH = OUTPUT_DIR / "probe_experiment.svg"


@dataclass(frozen=True)
class Measurement:
    requested_load: float
    actual_load: float
    entries: int
    successful_probes: float
    successful_theory: float
    failed_probes: float
    failed_theory: float


def measure_load(requested_load: float, rng: random.Random) -> Measurement:
    entries = round(requested_load * CAPACITY)
    # HashTable is fixed-capacity and never resizes, equivalent to max_load=None.
    table = HashTable(capacity=CAPACITY)
    urls = []

    for index in range(entries):
        url = f"https://example.com/{index}-{rng.getrandbits(128):032x}"
        table.put(url, str(index))
        urls.append(url)

    # Query every stored URL, in random order, for the successful-search mean.
    rng.shuffle(urls)
    successful_total = 0
    for url in urls:
        value, probes = table.find_with_probes(url)
        if value is None:
            raise RuntimeError(f"inserted URL was not found: {url}")
        successful_total += probes
    successful_mean = successful_total / entries

    failed_total = 0
    for index in range(FAILED_QUERIES):
        url = f"https://missing.example/{index}-{rng.getrandbits(128):032x}"
        value, probes = table.find_with_probes(url)
        if value is not None:
            raise RuntimeError(f"failure-query URL was found: {url}")
        failed_total += probes
    failed_mean = failed_total / FAILED_QUERIES

    actual_load = entries / CAPACITY
    return Measurement(
        requested_load=requested_load,
        actual_load=actual_load,
        entries=entries,
        successful_probes=successful_mean,
        successful_theory=1 + actual_load / 2,
        failed_probes=failed_mean,
        failed_theory=actual_load,
    )


def write_csv(measurements: list[Measurement]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "requested_load",
                "actual_load",
                "capacity",
                "entries",
                "failed_queries",
                "successful_probes_measured",
                "successful_probes_theory",
                "failed_probes_measured",
                "failed_probes_theory",
            )
        )
        for result in measurements:
            writer.writerow(
                (
                    f"{result.requested_load:.2f}",
                    f"{result.actual_load:.6f}",
                    CAPACITY,
                    result.entries,
                    FAILED_QUERIES,
                    f"{result.successful_probes:.6f}",
                    f"{result.successful_theory:.6f}",
                    f"{result.failed_probes:.6f}",
                    f"{result.failed_theory:.6f}",
                )
            )


def print_table(measurements: list[Measurement]) -> None:
    headers = (
        "alpha",
        "actual",
        "n",
        "success measured",
        "success theory",
        "failure measured",
        "failure theory",
    )
    rows = [
        (
            f"{result.requested_load:.2f}",
            f"{result.actual_load:.4f}",
            str(result.entries),
            f"{result.successful_probes:.4f}",
            f"{result.successful_theory:.4f}",
            f"{result.failed_probes:.4f}",
            f"{result.failed_theory:.4f}",
        )
        for result in measurements
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.rjust(widths[index]) for index, value in enumerate(row)))


def write_svg(measurements: list[Measurement]) -> None:
    width, height = 1000, 600
    left, top, plot_width, plot_height = 80, 70, 650, 420
    right = left + plot_width
    bottom = top + plot_height
    max_value = max(
        result.failed_probes
        for result in measurements
    )
    y_max = max(5, math.ceil(max_value + 0.5))

    def x_position(load: float) -> float:
        return left + (load - LOAD_FACTORS[0]) / (
            LOAD_FACTORS[-1] - LOAD_FACTORS[0]
        ) * plot_width

    def y_position(value: float) -> float:
        return bottom - value / y_max * plot_height

    series = (
        ("Successful measured", "#2563eb", "solid", "successful_probes"),
        ("Successful theory", "#2563eb", "dashed", "successful_theory"),
        ("Failed measured", "#dc2626", "solid", "failed_probes"),
        ("Failed theory", "#dc2626", "dashed", "failed_theory"),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<title>Hash table average probe counts by load factor</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="500" y="32" text-anchor="middle" font-size="20">'
        "Average probes by load factor</text>",
    ]

    for tick in range(y_max + 1):
        y = y_position(tick)
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" '
            'stroke="#e5e7eb"/>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" '
            f'font-size="12">{tick}</text>'
        )

    for tick in (0.25, 1, 2, 3, 4):
        x = x_position(tick)
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" '
            'stroke="#f3f4f6"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{bottom + 22}" text-anchor="middle" '
            f'font-size="12">{tick:.2f}</text>'
        )

    parts.extend(
        (
            f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" '
            'stroke="#111827"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" '
            'stroke="#111827"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 28}" '
            'text-anchor="middle" font-size="14">Load factor (alpha)</text>',
            f'<text x="20" y="{top + plot_height / 2}" '
            'transform="rotate(-90 20 '
            f'{top + plot_height / 2})" text-anchor="middle" font-size="14">'
            "Average compared nodes</text>",
        )
    )

    for label, color, style, attribute in series:
        points = " ".join(
            f"{x_position(result.actual_load):.2f},"
            f"{y_position(getattr(result, attribute)):.2f}"
            for result in measurements
        )
        dash = ' stroke-dasharray="6 4"' if style == "dashed" else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        if style == "solid":
            for result in measurements:
                parts.append(
                    f'<circle cx="{x_position(result.actual_load):.2f}" '
                    f'cy="{y_position(getattr(result, attribute)):.2f}" '
                    f'r="3" fill="{color}"/>'
                )

    for index, (label, color, style, _) in enumerate(series):
        y = top + 20 + index * 24
        dash = ' stroke-dasharray="6 4"' if style == "dashed" else ""
        parts.append(
            f'<line x1="770" y1="{y}" x2="805" y2="{y}" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        parts.append(
            f'<text x="815" y="{y + 5}" font-size="13">{label}</text>'
        )

    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    measurements = [
        measure_load(load_factor, rng) for load_factor in LOAD_FACTORS
    ]
    write_csv(measurements)
    write_svg(measurements)
    print_table(measurements)
    print(f"\nCSV: {CSV_PATH}")
    print(f"SVG: {SVG_PATH}")


if __name__ == "__main__":
    main()
