"""The instrument tutorial guides (songmap/instruments/guides.yaml) match the instruments' code."""
from __future__ import annotations

import os
import re

import numpy as np
import pytest
import yaml

from songmap.instruments import REGISTRY, Note, Sampler, make

GUIDES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "songmap", "instruments", "guides.yaml")
REQUIRED = ("title", "family", "ancestor", "summary", "how", "why", "chain", "params", "velocity",
            "recipes", "try_next")
BLOCK_KEYS = ("id", "label", "kind", "what", "params", "to")
KINDS = {"osc", "noise", "filter", "env", "shaper", "physical", "modal", "mix", "fx", "lfo", "pitch", "amp"}
PATTERN = re.compile(r"^[Xx\-o.]{16}$")

CLASSES = {**REGISTRY, "sampler": Sampler}


@pytest.fixture(scope="module")
def guides() -> dict:
    with open(GUIDES, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _spec(name: str) -> dict:
    return {q.name: q for q in CLASSES[name].PARAMS}


def test_every_instrument_has_a_guide(guides):
    assert set(CLASSES) <= set(guides), f"missing guides: {sorted(set(CLASSES) - set(guides))}"
    assert set(guides) <= set(CLASSES), f"guides for unknown instruments: {sorted(set(guides) - set(CLASSES))}"


@pytest.mark.parametrize("name", list(CLASSES))
def test_guide_shape(guides, name):
    g = guides[name]
    for k in REQUIRED:
        assert g.get(k), f"{name}: missing or empty '{k}'"
    assert g["family"] == CLASSES[name].family
    spec = _spec(name)
    assert set(g["params"]) == set(spec), f"{name}: params differ from PARAMS"
    for p, text in g["params"].items():
        for k in ("says", "up", "down"):
            assert isinstance(text.get(k), str) and text[k].strip(), f"{name}.{p}: missing '{k}'"


@pytest.mark.parametrize("name", list(CLASSES))
def test_chain(guides, name):
    chain = guides[name]["chain"]
    spec = _spec(name)
    ids = [b["id"] for b in chain]
    assert len(ids) == len(set(ids)), f"{name}: duplicate block ids"
    covered = set()
    for b in chain:
        for k in BLOCK_KEYS:
            assert k in b, f"{name}.{b.get('id')}: missing '{k}'"
        assert b["kind"] in KINDS, f"{name}.{b['id']}: kind '{b['kind']}'"
        assert set(b["params"]) <= set(spec), f"{name}.{b['id']}: unknown params {set(b['params']) - set(spec)}"
        covered |= set(b["params"])
        assert b["to"], f"{name}.{b['id']}: feeds nothing"
        for t in b["to"]:
            assert t == "out" or t in ids, f"{name}.{b['id']}: feeds unknown block '{t}'"
    assert covered == set(spec), f"{name}: params in no block: {set(spec) - covered}"
    assert any("out" in b["to"] for b in chain), f"{name}: nothing feeds 'out'"


@pytest.mark.parametrize("name", list(CLASSES))
def test_recipes_in_range(guides, name):
    recipes = guides[name]["recipes"]
    assert 3 <= len(recipes) <= 5
    spec = _spec(name)
    for r in recipes:
        assert r.get("name") and r.get("listen") and r.get("set")
        for k, v in r["set"].items():
            assert k in spec, f"{name} / {r['name']}: unknown param '{k}'"
            assert spec[k].lo <= v <= spec[k].hi, f"{name} / {r['name']}: {k}={v} outside [{spec[k].lo}, {spec[k].hi}]"


@pytest.mark.parametrize("name", list(CLASSES))
def test_pattern(guides, name):
    g = guides[name]
    if CLASSES[name].family == "drum":
        assert "pattern" in g, f"{name}: drums need an audition pattern"
    if "pattern" in g:
        assert PATTERN.match(g["pattern"]), f"{name}: bad pattern {g['pattern']!r}"


@pytest.mark.parametrize("name", list(REGISTRY))   # the sampler needs an optional library on disk
def test_recipes_render(guides, name):
    for r in guides[name]["recipes"]:
        y = make(name, **r["set"]).render(Note(60, 0.8, 0.5))
        assert np.all(np.isfinite(y)), f"{name} / {r['name']}: non-finite samples"
        assert np.max(np.abs(y)) > 1e-3, f"{name} / {r['name']}: silent"
