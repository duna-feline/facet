// Chart tooltips: <div class="f-bars" data-f-chart> shows a tooltip over the column under the
// pointer, or the one the keyboard picks. Marks are its .f-bars__col items, or any [data-f-tip]
// element. A mark's tooltip is data-f-tip if it has one, else its .f-bars__x text in bold over its
// .f-bars__tip text. The tooltip only repeats what the markup already says as text, so the chart
// reads the same without this module.
// Keys: the chart takes focus once (tabindex="0" is added when missing); ArrowLeft and ArrowRight,
// Home and End move between marks; Escape hides the tooltip. A visually hidden live region
// announces the mark the keyboard lands on. A tap shows a mark's tooltip on touch screens.
// Cleanup removes the tooltip, the live region and any tabindex this module added.
const done = new WeakSet();
const MARK = ".f-bars__col, [data-f-tip]";

export function init(root = document) {
  const off = [];
  for (const chart of root.querySelectorAll("[data-f-chart]")) {
    if (done.has(chart)) continue;
    const marks = [...chart.querySelectorAll(MARK)];
    if (!marks.length) continue;
    done.add(chart);
    const tip = document.createElement("div");
    tip.className = "f-tooltip";
    tip.setAttribute("aria-hidden", "true");
    tip.hidden = true;
    const live = document.createElement("span");
    live.className = "f-visually-hidden";
    live.setAttribute("aria-live", "polite");
    chart.append(tip, live);
    const addedTab = !chart.hasAttribute("tabindex");
    if (addedTab) chart.tabIndex = 0;
    let active = -1;

    const parts = (m) => {
      if (m.dataset.fTip) return ["", m.dataset.fTip];
      const text = (sel) => m.querySelector(sel)?.textContent.trim() || "";
      return [text(".f-bars__x"), text(".f-bars__tip")];
    };
    const show = (i, announce) => {
      if (active >= 0) marks[active]?.classList.remove("is-active");
      active = i;
      const m = marks[i];
      m.classList.add("is-active");
      const [head, body] = parts(m);
      tip.replaceChildren();
      if (head) {
        const b = document.createElement("b");
        b.textContent = head;
        tip.append(b);
      }
      tip.append(body);
      tip.hidden = false;
      // Over the mark's highest bar, centered on it, kept inside the chart's width; it may rise
      // above the plot, over the chart's title or legend.
      const box = chart.getBoundingClientRect();
      const bars = [...m.querySelectorAll(".f-bars__bar")].map((b) => b.getBoundingClientRect());
      const r = m.getBoundingClientRect();
      const top = Math.min(...bars.map((b) => b.top), bars.length ? Infinity : r.top);
      const w = tip.offsetWidth;
      const x = r.left + r.width / 2 - box.left - w / 2;
      tip.style.left = `${Math.max(0, Math.min(x, box.width - w))}px`;
      tip.style.top = `${top - box.top - tip.offsetHeight - 6}px`;
      if (announce) live.textContent = [head, body].filter(Boolean).join(": ");
    };
    const hide = () => {
      if (active >= 0) marks[active]?.classList.remove("is-active");
      tip.hidden = true;
    };

    const onOver = (e) => {
      const i = marks.indexOf(e.target.closest?.(MARK));
      if (i >= 0) show(i, false);
    };
    const onLeave = () => {
      if (document.activeElement !== chart) hide();
    };
    const onKey = (e) => {
      const keys = { ArrowRight: 1, ArrowLeft: -1, Home: -Infinity, End: Infinity };
      if (e.key === "Escape") {
        hide();
        return;
      }
      if (!(e.key in keys)) return;
      e.preventDefault();
      const step = keys[e.key];
      const from = active < 0 ? (step > 0 ? -1 : marks.length) : active;
      show(Math.max(0, Math.min(marks.length - 1, from + step)), true);
    };
    const onFocus = () => show(active < 0 ? 0 : active, true);

    chart.addEventListener("pointerover", onOver);
    chart.addEventListener("pointerdown", onOver);
    chart.addEventListener("pointerleave", onLeave);
    chart.addEventListener("keydown", onKey);
    chart.addEventListener("focus", onFocus);
    chart.addEventListener("blur", hide);
    off.push(() => {
      chart.removeEventListener("pointerover", onOver);
      chart.removeEventListener("pointerdown", onOver);
      chart.removeEventListener("pointerleave", onLeave);
      chart.removeEventListener("keydown", onKey);
      chart.removeEventListener("focus", onFocus);
      chart.removeEventListener("blur", hide);
      hide();
      tip.remove();
      live.remove();
      if (addedTab) chart.removeAttribute("tabindex");
      done.delete(chart);
    });
  }
  return () => off.forEach((f) => f());
}
