"""Contract tests: every implementation matches the interfaces exactly.

If these fail, code and interfaces have drifted apart. Fix the code, or change
the interface properly ($hack-interface). Never loosen these tests to make them pass.
"""

import inspect

import pytest

from PROJECT import interfaces  # replace PROJECT with the package name
# Register every implementation here: (implementation class, interface it implements)
from PROJECT.loading import CsvLoader  # example
from PROJECT.rules import ThresholdRules  # example

IMPLEMENTATIONS = [
    (CsvLoader, interfaces.Loader),
    (ThresholdRules, interfaces.RuleEngine),
]


def _public_methods(cls):
    return {
        name: member
        for name, member in inspect.getmembers(cls, inspect.isfunction)
        if not name.startswith("_")
    }


def _params(func):
    """Parameter names and kinds only. Type annotations are not compared,
    so harmless differences in how a type is written never fail the test."""
    return [(p.name, p.kind) for p in inspect.signature(func).parameters.values()]


@pytest.mark.parametrize("impl, iface", IMPLEMENTATIONS)
def test_implements_every_method(impl, iface):
    expected = _public_methods(iface)
    actual = _public_methods(impl)
    for name, iface_method in expected.items():
        assert name in actual, f"{impl.__name__} is missing {name}() from {iface.__name__}"
        assert _params(actual[name]) == _params(iface_method), (
            f"{impl.__name__}.{name} takes different parameters than {iface.__name__}.{name}"
        )


def test_sample_data_matches_input_columns():
    """The sample data in data/ must have exactly the columns the interface promises."""
    import csv
    from pathlib import Path

    sample = Path("data/sample.csv")
    if not sample.exists():
        pytest.skip("no data/sample.csv yet")
    with sample.open(newline="", encoding="utf-8-sig") as f:
        header = tuple(next(csv.reader(f)))
    assert header == interfaces.INPUT_COLUMNS
