// Select: a dropdown of checkboxes, or of radios for a single choice.
//   <details class="f-select" data-f-select>
//     <summary class="f-select__trigger">
//       <span class="f-select__label">Project</span><span class="f-select__value">All</span>
//     </summary>
//     <div class="f-select__panel">
//       <input class="f-input f-search f-select__search" type="search" aria-label="Filter" hidden />
//       <div class="f-select__list" role="group" aria-label="Project">
//         <label class="f-select__option"><input type="checkbox" name="p" value="a" />A</label>
//       </div>
//       <p class="f-select__empty" role="status" hidden>No matches</p>
//       <div class="f-select__foot" hidden>
//         <button class="f-btn f-btn--quiet" type="button" data-f-select-clear>Clear</button>
//         <button class="f-btn" type="button" data-f-select-done>Done</button>
//       </div>
//     </div>
//   </details>
// Without JS it is a disclosure of real form controls: it opens and closes, the boxes toggle and
// submit with a form, and the search and the footer stay hidden. This module shows them and adds:
// - The value text: data-f-select-none (no option checked, default "All"), the option's own text
//   (one checked), or data-f-select-many with {n} replaced (default "{n} selected"). Dispatch a
//   change event on the element to redraw it, for example after switching the language.
// - The search: typing filters the options by their text; .f-select__empty shows when none match.
// - Keys: ArrowDown or ArrowUp on the trigger opens it; arrows, Home and End move between the
//   search and the visible options; Space toggles; Enter or Escape closes and returns focus to the
//   trigger; a printable key on an option goes to the search.
// - Clear unchecks every option and dispatches change; Done closes. A click outside, or focus
//   moving out, closes. A single choice (radios) closes when an option is picked with the pointer.
// - On wide screens a panel that would cross the window's right edge shifts left.
// Changes apply at once: the boxes fire their own change events, which bubble.
const done = new WeakSet();
const OPTION = 'input[type="checkbox"], input[type="radio"]';
const WIDE = "(min-width: 641px)";

export function init(root = document) {
  const off = [];
  for (const el of root.querySelectorAll("details[data-f-select]")) {
    const trigger = el.querySelector(":scope > summary");
    const panel = el.querySelector(":scope > .f-select__panel");
    if (done.has(el) || !trigger || !panel) continue;
    done.add(el);
    const search = panel.querySelector(".f-select__search");
    const empty = panel.querySelector(".f-select__empty");
    const value = trigger.querySelector(".f-select__value");
    const shown = [search, panel.querySelector(".f-select__foot")].filter(Boolean);
    const wasHidden = shown.map((n) => n.hidden);
    const wasValue = value?.textContent;
    shown.forEach((n) => (n.hidden = false));

    const options = () => [...panel.querySelectorAll(OPTION)];
    const rowOf = (o) => o.closest(".f-select__option") || o;
    const visible = () => options().filter((o) => !rowOf(o).hidden && !o.disabled);
    const textOf = (o) => (o.closest("label")?.textContent || o.value).trim();

    const update = () => {
      if (!value) return;
      const on = options().filter((o) => o.checked);
      const text =
        on.length === 0
          ? el.dataset.fSelectNone || "All"
          : on.length === 1
            ? textOf(on[0])
            : (el.dataset.fSelectMany || "{n} selected").replace("{n}", on.length);
      if (value.textContent !== text) value.textContent = text;
    };
    const filter = () => {
      const q = search ? search.value.trim().toLocaleLowerCase() : "";
      let hits = 0;
      for (const o of options()) {
        const hit = !q || textOf(o).toLocaleLowerCase().includes(q);
        rowOf(o).hidden = !hit;
        hits += hit;
      }
      if (empty) empty.hidden = hits > 0;
    };
    const place = () => {
      el.style.removeProperty("--f-select-shift");
      if (!matchMedia(WIDE).matches) return;
      const r = panel.getBoundingClientRect();
      const edge = document.documentElement.clientWidth - 8;
      if (r.right > edge) {
        el.style.setProperty("--f-select-shift", `${-Math.min(r.right - edge, r.left - 8)}px`);
      }
    };
    const clearSearch = () => {
      if (search && search.value) {
        search.value = "";
        filter();
      }
    };
    const close = (refocus) => {
      el.open = false;
      clearSearch();
      if (refocus) trigger.focus();
    };
    const stops = () => [...(search ? [search] : []), ...visible()];
    const go = (target) => target?.focus();

    let pointer = false;
    const onToggle = () => {
      if (el.open) place();
      else clearSearch();
    };
    const onKey = (e) => {
      pointer = false;
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const t = e.target;
      if (e.key === "Escape" && el.open) {
        e.preventDefault();
        close(true);
        return;
      }
      if (t === trigger) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          el.open = true;
          go(search || visible().find((o) => o.checked) || visible()[0]);
        }
        return;
      }
      if (!panel.contains(t)) return;
      const isOption = t.matches(OPTION);
      // Radios move with their own arrow keys (which also pick); only the search hands over.
      const native = isOption && t.type === "radio";
      const list = stops();
      const i = list.indexOf(t);
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && i >= 0 && !native) {
        e.preventDefault();
        const step = e.key === "ArrowDown" ? 1 : -1;
        go(list[Math.min(list.length - 1, Math.max(0, i + step))]);
      } else if ((e.key === "Home" || e.key === "End") && isOption && !native) {
        e.preventDefault();
        const opts = visible();
        go(e.key === "Home" ? opts[0] : opts.at(-1));
      } else if (e.key === "Enter" && t === search) {
        e.preventDefault();
        go(visible().find((o) => o.checked) || visible()[0]);
      } else if (e.key === "Enter" && isOption) {
        e.preventDefault();
        close(true);
      } else if (search && isOption && e.key.length === 1 && e.key !== " ") {
        // Focus moves before the key's default action, so the character lands in the search.
        search.focus();
      }
    };
    const onPointer = () => (pointer = true);
    const onChange = (e) => {
      update();
      if (pointer && e.target.type === "radio") close(true);
      pointer = false;
    };
    const onClick = (e) => {
      const b = e.target.closest?.("[data-f-select-clear], [data-f-select-done]");
      if (!b || !panel.contains(b)) return;
      if (b.hasAttribute("data-f-select-done")) {
        close(true);
        return;
      }
      for (const o of options()) o.checked = false;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      go(search || visible()[0]);
    };
    const onOutside = (e) => {
      if (el.open && !el.contains(e.target)) close(false);
    };
    const onFocusOut = (e) => {
      if (el.open && e.relatedTarget && !el.contains(e.relatedTarget)) close(false);
    };

    el.addEventListener("toggle", onToggle);
    el.addEventListener("keydown", onKey);
    el.addEventListener("change", onChange);
    el.addEventListener("click", onClick);
    el.addEventListener("focusout", onFocusOut);
    panel.addEventListener("pointerdown", onPointer);
    search?.addEventListener("input", filter);
    document.addEventListener("pointerdown", onOutside);
    update();
    if (el.open) place();

    off.push(() => {
      el.removeEventListener("toggle", onToggle);
      el.removeEventListener("keydown", onKey);
      el.removeEventListener("change", onChange);
      el.removeEventListener("click", onClick);
      el.removeEventListener("focusout", onFocusOut);
      panel.removeEventListener("pointerdown", onPointer);
      search?.removeEventListener("input", filter);
      document.removeEventListener("pointerdown", onOutside);
      if (search) search.value = "";
      for (const o of options()) rowOf(o).hidden = false;
      if (empty) empty.hidden = true;
      shown.forEach((n, i) => (n.hidden = wasHidden[i]));
      if (value) value.textContent = wasValue;
      el.style.removeProperty("--f-select-shift");
      done.delete(el);
    });
  }
  return () => off.forEach((f) => f());
}
