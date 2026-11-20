"""Compare separate-chaining and linear-probing search costs."""

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable, HashTableProtocol, LinearProbingHashTable

CAPACITY = 4093
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
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
    chaining_successful_probes: float
    chaining_successful_theory: float
    chaining_failed_probes: float
    chaining_failed_theory: float
    linear_successful_probes: float
    linear_successful_theory: float
    linear_failed_probes: float
    linear_failed_theory: float


def measure_table(
    table: HashTableProtocol, urls: list[str], missing_urls: list[str]
) -> tuple[float, float]:
    successful_total = 0
    for url in urls:
        value, probes = table.find_with_probes(url)
        if value is None:
            raise RuntimeError(f"inserted URL was not found: {url}")
        successful_total += probes

    failed_total = 0
    for url in missing_urls:
        value, probes = table.find_with_probes(url)
        if value is not None:
            raise RuntimeError(f"failure-query URL was found: {url}")
        failed_total += probes

    return successful_total / len(urls), failed_total / len(missing_urls)


def measure_load(requested_load: float, rng: random.Random) -> Measurement:
    entries = round(requested_load * CAPACITY)
    urls = [
        f"https://example.com/{index}-{rng.getrandbits(128):032x}"
        for index in range(entries)
    ]
    chaining = HashTable(capacity=CAPACITY)
    linear = LinearProbingHashTable(capacity=CAPACITY)
    for index, url in enumerate(urls):
        chaining.put(url, str(index))
        linear.put(url, str(index))

    successful_queries = list(urls)
    rng.shuffle(successful_queries)
    missing_urls = [
        f"https://missing.example/{index}-{rng.getrandbits(128):032x}"
        for index in range(FAILED_QUERIES)
    ]
    chaining_success, chaining_failed = measure_table(
        chaining, successful_queries, missing_urls
    )
    linear_success, linear_failed = measure_table(
        linear, successful_queries, missing_urls
    )

    actual_load = entries / CAPACITY
    return Measurement(
        requested_load=requested_load,
        actual_load=actual_load,
        entries=entries,
        chaining_successful_probes=chaining_success,
        chaining_successful_theory=1 + actual_load / 2,
        chaining_failed_probes=chaining_failed,
        chaining_failed_theory=actual_load,
        linear_successful_probes=linear_success,
        linear_successful_theory=0.5 * (1 + 1 / (1 - actual_load)),
        linear_failed_probes=linear_failed,
        linear_failed_theory=0.5 * (1 + 1 / (1 - actual_load) ** 2),
    )


def write_csv(measurements: list[Measurement]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "requested_load",
                "actual_load",
                "capacity",
                "entries",
                "failed_queries",
                "chaining_successful_probes_measured",
                "chaining_successful_probes_theory",
                "chaining_failed_probes_measured",
                "chaining_failed_probes_theory",
                "linear_successful_probes_measured",
                "linear_successful_probes_theory",
                "linear_failed_probes_measured",
                "linear_failed_probes_theory",
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
                    f"{result.chaining_successful_probes:.6f}",
                    f"{result.chaining_successful_theory:.6f}",
                    f"{result.chaining_failed_probes:.6f}",
                    f"{result.chaining_failed_theory:.6f}",
                    f"{result.linear_successful_probes:.6f}",
                    f"{result.linear_successful_theory:.6f}",
                    f"{result.linear_failed_probes:.6f}",
                    f"{result.linear_failed_theory:.6f}",
                )
            )


def print_table(measurements: list[Measurement]) -> None:
    headers = (
        "alpha",
        "n",
        "chain success M/T",
        "linear success M/T",
        "chain failure M/T",
        "linear failure M/T",
    )
    rows = [
        (
            f"{result.actual_load:.3f}",
            str(result.entries),
            f"{result.chaining_successful_probes:.3f}/"
            f"{result.chaining_successful_theory:.3f}",
            f"{result.linear_successful_probes:.3f}/"
            f"{result.linear_successful_theory:.3f}",
            f"{result.chaining_failed_probes:.3f}/"
            f"{result.chaining_failed_theory:.3f}",
            f"{result.linear_failed_probes:.3f}/"
            f"{result.linear_failed_theory:.3f}",
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
    width, height = 1200, 620
    plot_top, plot_height, plot_width = 100, 410, 450
    colors = {"chaining": "#2563eb", "linear": "#dc2626"}
    panels = (
        (
            "Successful searches",
            (
                ("Chaining measured", "chaining", False, "chaining_successful_probes"),
                ("Chaining theory", "chaining", True, "chaining_successful_theory"),
                ("Linear measured", "linear", False, "linear_successful_probes"),
                ("Linear theory", "linear", True, "linear_successful_theory"),
            ),
        ),
        (
            "Failed searches",
            (
                ("Chaining measured", "chaining", False, "chaining_failed_probes"),
                ("Chaining theory", "chaining", True, "chaining_failed_theory"),
                ("Linear measured", "linear", False, "linear_failed_probes"),
                ("Linear theory", "linear", True, "linear_failed_theory"),
            ),
        ),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<title>Average hash-table probes by load factor</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="600" y="30" text-anchor="middle" font-size="20">'
        "Separate chaining vs. linear probing</text>",
    ]

    for panel_index, (title, series) in enumerate(panels):
        panel_x = 35 + panel_index * 590
        plot_left = panel_x + 60
        plot_right = plot_left + plot_width
        plot_bottom = plot_top + plot_height
        max_value = max(
            getattr(result, attribute)
            for result in measurements
            for _, _, _, attribute in series
        )
        y_max = max(1, math.ceil(max_value * 1.1))
        y_step = max(1, math.ceil(y_max / 5))

        parts.append(
            f'<text x="{panel_x + 280}" y="62" text-anchor="middle" '
            f'font-size="17">{title}</text>'
        )
        for series_index, (label, strategy, dashed, _) in enumerate(series):
            legend_x = panel_x + 28 + (series_index % 2) * 265
            legend_y = 82 + (series_index // 2) * 19
            dash = ' stroke-dasharray="6 4"' if dashed else ""
            parts.append(
                f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 25}" '
                f'y2="{legend_y}" stroke="{colors[strategy]}" stroke-width="2"{dash}/>'
            )
            parts.append(
                f'<text x="{legend_x + 32}" y="{legend_y + 4}" font-size="11">'
                f"{label}</text>"
            )

        def x_position(load: float) -> float:
            return plot_left + (load - LOAD_FACTORS[0]) / (
                LOAD_FACTORS[-1] - LOAD_FACTORS[0]
            ) * plot_width

        def y_position(value: float) -> float:
            return plot_bottom - value / y_max * plot_height

        for tick in range(0, y_max + 1, y_step):
            y = y_position(tick)
            parts.append(
                f'<line x1="{plot_left}" y1="{y:.2f}" x2="{plot_right}" '
                f'y2="{y:.2f}" stroke="#e5e7eb"/>'
            )
            parts.append(
                f'<text x="{plot_left - 10}" y="{y + 4:.2f}" text-anchor="end" '
                f'font-size="11">{tick}</text>'
            )

        for tick in range(1, 10, 2):
            load = tick / 10
            x = x_position(load)
            parts.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" '
                f'y2="{plot_bottom}" stroke="#f3f4f6"/>'
            )
            parts.append(
                f'<text x="{x:.2f}" y="{plot_bottom + 20}" text-anchor="middle" '
                f'font-size="11">{load:.1f}</text>'
            )

        parts.extend(
            (
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" '
                f'y2="{plot_bottom}" stroke="#111827"/>',
                f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" '
                f'y2="{plot_bottom}" stroke="#111827"/>',
                f'<text x="{plot_left + plot_width / 2}" y="{plot_bottom + 45}" '
                'text-anchor="middle" font-size="13">Load factor (alpha)</text>',
                f'<text x="{panel_x + 15}" y="{plot_top + plot_height / 2}" '
                f'transform="rotate(-90 {panel_x + 15} '
                f'{plot_top + plot_height / 2})" text-anchor="middle" '
                'font-size="13">Average probes</text>',
            )
        )

        for _, strategy, dashed, attribute in series:
            points = " ".join(
                f"{x_position(result.actual_load):.2f},"
                f"{y_position(getattr(result, attribute)):.2f}"
                for result in measurements
            )
            dash = ' stroke-dasharray="6 4"' if dashed else ""
            parts.append(
                f'<polyline points="{points}" fill="none" '
                f'stroke="{colors[strategy]}" stroke-width="2"{dash}/>'
            )
            if not dashed:
                for result in measurements:
                    parts.append(
                        f'<circle cx="{x_position(result.actual_load):.2f}" '
                        f'cy="{y_position(getattr(result, attribute)):.2f}" '
                        f'r="3" fill="{colors[strategy]}"/>'
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
