"""Select: the dropdown of checkboxes (or radios) on the components page."""

import pytest
from checks import contrast, focus_ring, no_hscroll

FACET = "import('/dist/js/facet.js')"
SEL = "#demo-select"
LONG = "#demo-select-long"
ONE = "#demo-select-one"


def is_open(page, sel=SEL):
    return page.evaluate(f"document.querySelector({sel!r}).open")


def value(page, sel=SEL):
    return page.inner_text(f"{sel} .f-select__value")


def focused(page):
    return page.evaluate(
        "(() => { const a = document.activeElement;"
        " return a.value || a.className || a.tagName; })()"
    )


def visible_options(page, sel):
    return page.evaluate(
        f"[...document.querySelectorAll('{sel} .f-select__option')]"
        ".filter(o => o.checkVisibility()).map(o => o.textContent.trim())"
    )


def test_value_text_follows_the_checked_options(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    assert value(page) == "All"
    page.click(f"{SEL} > summary")
    page.click(f"{SEL} input[value=hairball]")
    assert value(page) == "Hairball"
    page.click(f"{SEL} input[value=nap]")
    page.click(f"{SEL} input[value=sunbeam]")
    assert value(page) == "3 selected"
    page.click(f"{SEL} [data-f-select-clear]")
    assert value(page) == "All"
    assert page.evaluate(f"document.querySelectorAll('{SEL} input:checked').length") == 0


def test_changes_bubble_at_once(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    page.evaluate(
        f"window.__changes = 0; document.querySelector({SEL!r})"
        ".addEventListener('change', () => window.__changes++)"
    )
    page.click(f"{SEL} > summary")
    page.click(f"{SEL} input[value=hairball]")
    page.click(f"{SEL} [data-f-select-clear]")
    assert page.evaluate("window.__changes") == 2
    assert is_open(page)


def test_keyboard(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    page.focus(f"{SEL} > summary")
    page.keyboard.press("ArrowDown")
    assert is_open(page)
    assert "f-select__search" in focused(page)
    # Down from the search reaches the options; Space toggles; Up comes back.
    page.keyboard.press("ArrowDown")
    assert focused(page) == "purrometheus"
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Space")
    assert value(page) == "Hairball"
    page.keyboard.press("End")
    assert focused(page) == "nap"
    page.keyboard.press("Home")
    assert focused(page) == "purrometheus"
    # A printable key on an option goes to the search, which filters.
    page.keyboard.type("red")
    assert page.input_value(f"{SEL} .f-select__search") == "red"
    assert visible_options(page, SEL) == ["Red Dot Tracker"]
    # Escape closes, returns focus to the trigger and clears the search.
    page.keyboard.press("Escape")
    assert not is_open(page)
    assert page.evaluate("document.activeElement.matches('#demo-select > summary')")
    assert page.input_value(f"{SEL} .f-select__search") == ""
    # Enter on the trigger opens it natively; Enter on an option closes it.
    page.keyboard.press("Enter")
    assert is_open(page)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    assert not is_open(page)
    assert value(page) == "Hairball"


def test_search_filters_a_long_list_that_scrolls(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    page.click(f"{LONG} > summary")
    sizes = page.evaluate(
        f"(() => {{ const l = document.querySelector('{LONG} .f-select__list');"
        " return [l.children.length, l.scrollHeight, l.clientHeight]; })()"
    )
    assert sizes[0] == 120
    assert sizes[1] > sizes[2] * 3, "a long list scrolls inside a bounded panel"
    page.fill(f"{LONG} .f-select__search", "sunbeam-docs")
    assert visible_options(page, LONG) == [
        "sunbeam-docs",
        "sunbeam-docs-v2",
        "sunbeam-docs-old",
        "sunbeam-docs-next",
    ]
    page.fill(f"{LONG} .f-select__search", "no such repo")
    assert visible_options(page, LONG) == []
    assert page.is_visible(f"{LONG} .f-select__empty")


def test_single_choice_closes_on_pick(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    assert value(page, ONE) == "Newest"
    page.click(f"{ONE} > summary")
    page.click(f"{ONE} input[value=name]")
    assert not is_open(page, ONE)
    assert value(page, ONE) == "Name"
    # Arrow keys pick among radios and keep the panel open.
    page.focus(f"{ONE} > summary")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowUp")
    assert is_open(page, ONE)
    assert value(page, ONE) == "Oldest"


def test_click_outside_and_focus_leaving_close_it(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    page.click(f"{SEL} > summary")
    page.mouse.click(1200, 880)
    assert not is_open(page)
    page.click(f"{SEL} > summary")
    page.click(f"{SEL} [data-f-select-done]")
    assert not is_open(page)
    page.click(f"{SEL} > summary")
    page.focus(f"{LONG} > summary")
    assert not is_open(page)


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_readable_with_a_focus_ring_and_touch_sized_rows(page_factory, site_url, theme):
    page = page_factory(theme=theme)
    page.goto(f"{site_url}/components.html")
    assert contrast(page, f"{SEL} .f-select__value", f"{SEL} > summary") >= 4.5
    assert contrast(page, f"{SEL} .f-select__label", f"{SEL} > summary") >= 4.5
    page.click(f"{SEL} > summary")
    assert contrast(page, f"{SEL} .f-select__option", f"{SEL} .f-select__panel") >= 4.5
    heights = page.evaluate(
        f"[...document.querySelectorAll('{SEL} .f-select__option')]"
        ".map(o => o.getBoundingClientRect().height)"
    )
    assert min(heights) >= 44
    page.keyboard.press("Tab")
    page.focus(f"{SEL} input[value=hairball]")
    ring = page.evaluate(
        f"(() => {{ const s = getComputedStyle("
        f"document.querySelector('{SEL} input[value=hairball]').closest('label'));"
        " return [s.outlineStyle, s.outlineWidth]; })()"
    )
    assert ring == ["solid", "2px"]
    page.keyboard.press("Escape")
    assert not focus_ring(page, f"{SEL} > summary").startswith("none")


def test_bottom_sheet_on_phones(page_factory, site_url):
    page = page_factory(width=390, theme="light", lang="zh")
    page.goto(f"{site_url}/components.html")
    page.click(f"{LONG} > summary")
    page.evaluate(
        f"Promise.all(document.querySelector('{LONG} .f-select__panel').getAnimations()"
        ".map((a) => a.finished))"
    )
    box = page.evaluate(
        f"(() => {{ const r = document.querySelector('{LONG} .f-select__panel')"
        ".getBoundingClientRect();"
        " return [r.left, r.width, r.bottom, innerWidth, innerHeight]; })()"
    )
    left, width, bottom, vw, vh = box
    assert abs(left) < 1 and abs(width - vw) < 1 and abs(bottom - vh) < 1
    assert page.evaluate("getComputedStyle(document.documentElement).overflow") == "hidden"
    # The footer stays clear of the scrolling list.
    foot, list_bottom = page.evaluate(
        f"['.f-select__foot', '.f-select__list'].map(s =>"
        f" document.querySelector('{LONG} ' + s).getBoundingClientRect())"
        ".map((r, i) => i ? r.bottom : r.top)"
    )
    assert list_bottom <= foot
    # Chinese value text, then a tap on the dimmed page closes it.
    page.click(f"{LONG} input[value=hairball-api]")
    page.click(f"{LONG} input[value=hairball-web]")
    assert value(page, LONG) == "已选 2 项"
    page.mouse.click(195, 40)
    assert not is_open(page, LONG)
    no_hscroll(page)


def test_panel_stays_inside_the_window(page_factory, site_url):
    page = page_factory(width=860)
    page.goto(f"{site_url}/components.html")
    page.evaluate(
        f"(() => {{ const s = document.querySelector({SEL!r});"
        " s.parentElement.style.justifyContent = 'flex-end'; })()"
    )
    page.click(f"{SEL} > summary")
    right = page.evaluate(
        f"document.querySelector('{SEL} .f-select__panel').getBoundingClientRect().right"
    )
    assert right <= 860 - 8 + 0.5
    no_hscroll(page)


def test_works_without_js(page_factory, site_url):
    page = page_factory(js=False)
    page.goto(f"{site_url}/components.html")
    assert not page.is_visible(f"{SEL} .f-select__search")
    assert not page.is_visible(f"{SEL} .f-select__foot")
    page.click(f"{SEL} > summary")
    assert is_open(page)
    page.click(f"{SEL} input[value=hairball]")
    assert page.is_checked(f"{SEL} input[value=hairball]")
    # A click outside lands on the trigger's backdrop layer and closes it.
    page.mouse.click(1200, 880)
    assert not is_open(page)


def test_init_twice_and_cleanup(page_factory, site_url):
    page = page_factory()
    page.goto(f"{site_url}/components.html")
    page.evaluate(f"{FACET}.then((m) => {{ m.init(); m.init(); }})")
    page.click(f"{SEL} > summary")
    page.click(f"{SEL} input[value=hairball]")
    page.click(f"{SEL} input[value=nap]")
    assert value(page) == "2 selected"
    page.fill(f"{SEL} .f-select__search", "nap")
    page.evaluate(f"{FACET}.then((m) => m.cleanup())")
    assert value(page) == "All"
    assert not page.is_visible(f"{SEL} .f-select__search")
    assert len(visible_options(page, SEL)) == 5
    page.click(f"{SEL} input[value=sunbeam]")
    assert value(page) == "All"
