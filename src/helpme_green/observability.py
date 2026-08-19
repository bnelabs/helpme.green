from __future__ import annotations

import os
import re
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

MetricLabels = Mapping[str, str | int]
MetricKey = tuple[str, tuple[tuple[str, str], ...]]


def _labels(value: MetricLabels | None) -> tuple[tuple[str, str], ...]:
    if not value:
        return ()
    return tuple(sorted((str(key), str(item)) for key, item in value.items()))


def _metric_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", value).strip("_").lower()
    return "helpme_" + (normalized or "unnamed")


def _label_text(value: tuple[tuple[str, str], ...]) -> str:
    if not value:
        return ""
    rendered = []
    for key, item in value:
        safe_key = re.sub(r"[^a-zA-Z0-9_]", "_", key).strip("_") or "label"
        safe_value = item.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        rendered.append(f'{safe_key}="{safe_value}"')
    return "{" + ",".join(rendered) + "}"


class MetricsRegistry:
    """Small, dependency-free aggregate metrics registry.

    Metrics are deliberately opt-in and contain only bounded labels selected by the caller. No
    prompts, model responses, keys, image bytes, or session identifiers belong here.
    """

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled
        self._lock = threading.Lock()
        self._counters: dict[MetricKey, int] = {}
        self._gauges: dict[MetricKey, float] = {}
        self._timing_sums: dict[MetricKey, float] = {}
        self._timing_counts: dict[MetricKey, int] = {}

    @classmethod
    def from_environment(cls) -> MetricsRegistry:
        raw = os.environ.get("HELPME_METRICS_ENABLED", "")
        return cls(enabled=raw.casefold() in {"1", "true", "yes", "on"})

    def counter(self, name: str, amount: int = 1, *, labels: MetricLabels | None = None) -> None:
        if not self.enabled:
            return
        key = (name, _labels(labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def gauge(self, name: str, value: float, *, labels: MetricLabels | None = None) -> None:
        if not self.enabled:
            return
        key = (name, _labels(labels))
        with self._lock:
            self._gauges[key] = float(value)

    def adjust_gauge(self, name: str, amount: float, *, labels: MetricLabels | None = None) -> None:
        if not self.enabled:
            return
        key = (name, _labels(labels))
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0.0) + amount

    def observe(self, name: str, seconds: float, *, labels: MetricLabels | None = None) -> None:
        if not self.enabled:
            return
        key = (name, _labels(labels))
        with self._lock:
            self._timing_sums[key] = self._timing_sums.get(key, 0.0) + max(0.0, seconds)
            self._timing_counts[key] = self._timing_counts.get(key, 0) + 1

    @contextmanager
    def track(self, name: str, *, labels: MetricLabels | None = None) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        started = time.monotonic()
        self.adjust_gauge(f"{name}_active", 1, labels=labels)
        try:
            yield
        finally:
            self.adjust_gauge(f"{name}_active", -1, labels=labels)
            self.observe(f"{name}_duration_seconds", time.monotonic() - started, labels=labels)

    def prometheus(self) -> str:
        if not self.enabled:
            return ""
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            timing_sums = dict(self._timing_sums)
            timing_counts = dict(self._timing_counts)
        lines: list[str] = []
        for (name, labels), counter_value in sorted(counters.items()):
            metric = _metric_name(name)
            lines.append(f"# TYPE {metric} counter")
            lines.append(f"{metric}{_label_text(labels)} {counter_value}")
        for (name, labels), gauge_value in sorted(gauges.items()):
            metric = _metric_name(name)
            lines.append(f"# TYPE {metric} gauge")
            lines.append(f"{metric}{_label_text(labels)} {gauge_value:g}")
        for (name, labels), timing_value in sorted(timing_sums.items()):
            metric = _metric_name(name)
            lines.append(f"# TYPE {metric} summary")
            lines.append(f"{metric}_sum{_label_text(labels)} {timing_value:.9f}")
            lines.append(f"{metric}_count{_label_text(labels)} {timing_counts[(name, labels)]}")
        return "\n".join(lines) + ("\n" if lines else "")
