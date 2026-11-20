"""Charts: chart tokens, stat tiles, meters, bar charts, legends, tooltips, small multiples."""

import re
from itertools import pairwise
from pathlib import Path

import pytest
from checks import TO_RGB, _lum, contrast, no_hscroll

ROOT = Path(__file__).resolve().parents[1]
FACET = "import('/dist/js/facet.js')"
CHART = "#demo-chart .f-bars"
STACK = "#demo-stack .f-bars"

# The series in their fixed order, as (dark, light): one hue each, stepped in lightness.
SERIES = {
    "dark": [
        "oklch(0.665 0.105 255)",
        "oklch(0.54 0.105 330)",
        "oklch(0.6 0.105 55)",
        "oklch(0.665 0.105 295)",
        "oklch(0.54 0.105 165)",
    ],
    "light": [
        "oklch(0.44 0.105 255)",
        "oklch(0.62 0.105 330)",
        "oklch(0.53 0.105 55)",
        "oklch(0.44 0.105 295)",
        "oklch(0.62 0.105 165)",
    ],
}

RESOLVE = """(names) => names.map(v => {
  const p = document.createElement('i');
  p.style.background = `var(${v})`;
  document.body.append(p);
  const c = getComputedStyle(p).backgroundColor;
  p.remove();
  return c;
})"""


def ratio(a, b):
    hi, lo = sorted([_lum(a), _lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def rgb(page, colors):
    return page.evaluate(f"(cs) => cs.map(c => ({TO_RGB})(c))", colors)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_series_tokens_and_their_contrast(page_factory, site_url, theme):
    page = page_factory(theme=theme)
    page.goto(f"{site_url}/components.html")
    names = [f"--f-chart-{i}" for i in range(1, 6)]
    got = page.evaluate(RESOLVE, names)
    assert got == SERIES[theme]
    # Every mark keeps 3:1 against the chart surface.
    surface = rgb(page, page.evaluate(RESOLVE, ["--f-bg-2"]))[0]
    for name, color in zip(names, rgb(page, got), strict=True):
        assert ratio(color, surface) >= 3, (theme, name)


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("accent", [None, "rose", "moss", "teal"])
def test_magnitude_ramp_follows_the_accent_and_reads_as_a_ramp(
    page_factory, site_url, theme, accent
):
    page = page_factory(theme=theme, accent=accent)
    page.goto(f"{site_url}/components.html")
    names = [f"--f-seq-{i}" for i in range(1, 6)]
    ramp = page.evaluate(RESOLVE, names)
    lch = [
        tuple(map(float, re.match(r"oklch\(([\d.]+) ([\d.]+) ([\d.]+)", c).groups())) for c in ramp
    ]
    accent_hue = float(
        re.match(r"oklch\([\d.]+ [\d.]+ ([\d.]+)", page.evaluate(RESOLVE, ["--f-accent"])[0])[1]
    )
    lightness = [c[0] for c in lch]
    steps = [abs(b - a) for a, b in pairwise(lightness)]
    # Faint to strong: up in dark, down in light, every step visible.
    assert lightness == sorted(lightness, reverse=theme == "light")
    assert min(steps) >= 0.06
    assert all(c[2] == pytest.approx(accent_hue) for c in lch)
    surface = rgb(page, page.evaluate(RESOLVE, ["--f-bg-2"]))[0]
    assert ratio(rgb(page, [ramp[0]])[0], surface) >= 2


def test_magnitude_ramp_falls_back_to_slate(page_factory, site_url):
    # A browser without relative colors gets the plain Slate values.
    page = page_factory(accent="rose")
    page.route(
        "**/dist/facet.css",
        lambda route: route.fulfill(
            response=route.fetch(),
            body=route.fetch().text().replace("oklch(from", "nope(from"),
        ),
    )
    page.goto(f"{site_url}/components.html")
    assert page.evaluate(RESOLVE, ["--f-seq-1"]) == ["oklch(0.48 0.06 255)"]


def test_chroma_stays_low_outside_the_chart_series():
    # Facet's colors stay at chroma 0.08 or below; only the series colors may reach 0.105.
    for path in sorted((ROOT / "src/css").rglob("*.css")):
        css = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.S)
        for decl in re.findall(r"([\w-]+)\s*:([^;{}]*)", css):
            name, value = decl
            for c in re.findall(r"oklch\([\d.]+ ([\d.]+) [\d.]+", value):
                cap = 0.105 if name.startswith("--f-chart-") else 0.08
                assert float(c) <= cap, (path.name, name, c)


def bars(page, sel):
    return page.evaluate(
        f"""[...document.querySelectorAll('{sel} .f-bars__col')].map(col =>
          [...col.querySelectorAll('.f-bars__bar')].map(b => {{
            const r = b.getBoundingClientRect(), s = getComputedStyle(b);
            return {{top: r.top, bottom: r.bottom, h: r.height, w: r.width,
              content: b.clientHeight - parseFloat(s.paddingBottom),
              radius: [s.borderTopLeftRadius, s.borderBottomLeftRadius]}};
          }}))"""
    )


def test_bars_are_to_scale_thin_and_rounded_at_the_data_end(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    plot = page.evaluate(
        f"(() => {{ const r = document.querySelector('{CHART} .f-bars__plot')"
        ".getBoundingClientRect(); return [r.height, r.bottom]; })()"
    )
    cols = bars(page, CHART)
    values = [18, 26, 31, 22, 35, 12, 9]
    for (bar,), v in zip(cols, values, strict=True):
        assert bar["h"] == pytest.approx(plot[0] * v / 40, abs=0.6)
        assert bar["bottom"] == pytest.approx(plot[1], abs=0.6)
        assert bar["w"] <= 24
        assert bar["radius"] == ["4px", "0px"]


def test_stacked_bars_keep_a_gap_and_their_total(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    plot_h = page.evaluate(
        f"document.querySelector('{STACK} .f-bars__plot').getBoundingClientRect().height"
    )
    first = bars(page, STACK)[0]  # Mon: Duna 8, Dudu 6, Nangnang 4
    # Bottom to top in source order; the upper parts give 2px of their own height to the gap.
    assert first[0]["bottom"] > first[1]["bottom"] > first[2]["bottom"]
    total = first[0]["bottom"] - first[2]["top"]
    assert total == pytest.approx(plot_h * 18 / 40, abs=0.8)
    for lower, upper in pairwise(first):
        assert upper["bottom"] == pytest.approx(lower["top"], abs=0.6)
        assert upper["h"] - upper["content"] == pytest.approx(2, abs=0.1)
    assert [b["radius"][0] for b in first] == ["0px", "0px", "4px"]


def test_tooltip_on_hover_and_keyboard(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    tip = f"{STACK} .f-tooltip"
    assert not page.is_visible(tip)
    page.hover(f"{STACK} .f-bars__col:nth-child(3)")
    assert page.inner_text(tip) == "Wed\nDuna 7 · Dudu 12 · Nangnang 8"
    box, chart = page.evaluate(
        f"['{tip}', '{STACK}'].map(s => document.querySelector(s).getBoundingClientRect().toJSON())"
    )
    assert box["left"] >= chart["left"] - 0.5 and box["right"] <= chart["right"] + 0.5
    page.mouse.move(0, 0)
    assert not page.is_visible(tip)

    # Keyboard: focus the chart, move with the arrows, hear the value, Escape hides it.
    page.focus(CHART)
    page.keyboard.press("End")
    assert page.inner_text(f"{CHART} .f-tooltip") == "Sun\n9 attempts"
    assert (
        page.evaluate(f"document.querySelector('{CHART} [aria-live]').textContent")
        == "Sun: 9 attempts"
    )
    page.keyboard.press("ArrowLeft")
    assert page.inner_text(f"{CHART} .f-tooltip") == "Sat\n12 attempts"
    assert page.evaluate(f"document.querySelectorAll('{CHART} .is-active').length") == 1
    page.keyboard.press("Escape")
    assert not page.is_visible(f"{CHART} .f-tooltip")


def test_charts_read_as_text_without_js(page_factory, site_url):
    page = page_factory(js=False)
    page.goto(f"{site_url}/components.html")
    assert page.locator(".f-tooltip").count() == 0
    text = page.evaluate(f"document.querySelector('{CHART} .f-bars__col').textContent")
    assert "Mon" in text and "18 attempts" in text
    assert page.evaluate("document.querySelectorAll('.f-chart__table table').length") == 2


def test_meters(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    fill, track = page.evaluate(
        "['#demo-meter .f-meter__fill', '#demo-meter .f-meter__track']"
        ".map(s => document.querySelector(s).getBoundingClientRect().width)"
    )
    assert fill == pytest.approx(track * 0.62, abs=0.6)
    meters = page.evaluate(
        "[...document.querySelectorAll('.f-meter')].map(m => {"
        " const t = m.querySelector('[role=meter]');"
        " const f = m.querySelector('.f-meter__fill').getBoundingClientRect().width;"
        " return [+t.getAttribute('aria-valuenow') / +t.getAttribute('aria-valuemax'),"
        "  f / t.getBoundingClientRect().width,"
        "  getComputedStyle(m.querySelector('.f-meter__value'), '::before').maskImage]; })"
    )
    for share, drawn, _ in meters:
        assert drawn == pytest.approx(share, abs=0.01)
    # A warning meter carries an icon; a plain one does not.
    assert meters[1][2].startswith("url(") and meters[0][2] == "none"


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_chart_text_is_readable(page_factory, site_url, theme, lang):
    page = page_factory(theme=theme, lang=lang)
    page.goto(f"{site_url}/components.html")
    for sel, bg in [
        (".f-stat__label", ".f-stat"),
        (".f-stat__context", ".f-stat"),
        (".f-stat__value", ".f-stat"),
        ("#demo-chart .f-chart__sub", "#demo-chart"),
        (f"{CHART} .f-bars__y", "#demo-chart"),
        (f"{CHART} .f-bars__x", "#demo-chart"),
        ("#demo-stack .f-legend", "#demo-stack"),
        ("#demo-meter .f-meter__value", "body"),
        ("#demo-meter .f-meter__context", "body"),
        (".f-meter--warning .f-meter__value", "body"),
    ]:
        assert contrast(page, sel, bg) >= 4.5, (theme, lang, sel)


def test_stat_values_use_proportional_figures_and_axes_tabular(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    num = "(s) => getComputedStyle(document.querySelector(s)).fontVariantNumeric"
    assert "proportional-nums" in page.evaluate(num, ".f-stat__value")
    for sel in [f"{CHART} .f-bars__y", "#demo-meter .f-meter__value", ".f-chart__table table"]:
        assert "tabular-nums" in page.evaluate(num, sel), sel


def test_small_multiples_share_one_scale(page_factory, site_url):
    for width, columns in [(390, 1), (1280, 3)]:
        page = page_factory(width=width)
        page.goto(f"{site_url}/components.html")
        lefts = page.evaluate(
            "[...document.querySelectorAll('#multiples .f-chart')]"
            ".map(c => Math.round(c.getBoundingClientRect().left))"
        )
        assert len(set(lefts)) == columns
        # The same value draws the same height in every panel.
        heights = page.evaluate(
            "[...document.querySelectorAll('#multiples .f-chart')].map(c => {"
            " const p = c.querySelector('.f-bars__plot').getBoundingClientRect().height;"
            " return [...c.querySelectorAll('.f-bars__bar')].map(b =>"
            "  b.getBoundingClientRect().height / p * 14); })"
        )
        assert heights[0][0] == pytest.approx(8, abs=0.1)
        assert heights[2][2] == pytest.approx(8, abs=0.1)
        no_hscroll(page)


def test_init_twice_and_cleanup(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    page.evaluate(f"{FACET}.then((m) => {{ m.init(); m.init(); }})")
    assert page.evaluate(f"document.querySelectorAll('{CHART} .f-tooltip').length") == 1
    page.hover(f"{CHART} .f-bars__col")
    page.evaluate(f"{FACET}.then((m) => m.cleanup())")
    assert page.evaluate("document.querySelectorAll('.f-tooltip, .f-bars [aria-live]').length") == 0
    assert page.evaluate(f"document.querySelector('{CHART}').hasAttribute('tabindex')") is False
    assert page.evaluate("document.querySelectorAll('.f-bars__col.is-active').length") == 0
