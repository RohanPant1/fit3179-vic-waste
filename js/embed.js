/* Embed every chart, and wire the one thing that runs across all of them.

   Titles and captions live in index.html so the page controls typography;
   the specs carry only the graphic.

   "Find your council" is the custom element of this page. Vega-Lite cannot
   share a selection between separately embedded charts, so each spec that
   supports it declares a `focusCouncil` variable parameter, and the dropdown
   pushes the chosen name into every view through the Vega View API. One dark
   ring then follows the reader's own council down the page.

   BUILD is appended to every spec and data request. Browsers cache those
   fetches hard and a normal reload does not clear them, so without this a
   visitor can sit on a stale chart indefinitely. Bump it when specs or data
   change.

   Bump the ?v= on this file's own script tag in index.html at the same time,
   and the one on the stylesheet. This file cannot cache-bust itself: a
   returning visitor ran the previous embed.js against the current HTML, so it
   looked for chart ids that no longer existed and silently rendered nothing. */

const BUILD = "2026-10-27d";

const CHARTS = [
  { el: "#vis-finder",     spec: "specs/00-finder-strip.vl.json" },
  { el: "#vis-waffle",     spec: "specs/01-waffle-streams.vl.json" },
  { el: "#vis-mosaic",     spec: "specs/02-mosaic-volume-composition.vl.json" },
  { el: "#vis-kghousehold",spec: "specs/03-choropleth-kg-household.vl.json" },
  { el: "#vis-diversion",  spec: "specs/04-choropleth-diversion.vl.json" },
  { el: "#vis-beeswarm",   spec: "specs/05-beeswarm-groups.vl.json" },
  { el: "#vis-difference", spec: "specs/06-difference-recovery.vl.json" },
  { el: "#vis-dotplot",    spec: "specs/07-dotplot-bincount.vl.json" },
  { el: "#vis-facilities", spec: "specs/08-symbol-facilities.vl.json" },
  { el: "#vis-flow",       spec: "specs/09-flow-nogreenbin.vl.json" },
  { el: "#vis-dumbbell",   spec: "specs/10-dumbbell-cost.vl.json" },
  { el: "#vis-dorling",    spec: "specs/11-cost-dorling.vl.json" },
  { el: "#vis-bivariate",  spec: "specs/12-bivariate-seifa-diversion.vl.json" },
  { el: "#vis-barcode",    spec: "specs/13-barcode-seifa-service.vl.json" },
  { el: "#vis-stream",     spec: "specs/14-streamgraph-history.vl.json" },
  { el: "#vis-rollout",    spec: "specs/15-rollout-by-year.vl.json" }
];

const stamp = (url) => url + (url.includes("?") ? "&" : "?") + "v=" + BUILD;

const getText = (url) =>
  fetch(stamp(url), { cache: "no-cache" }).then((r) => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.text();
  });

const getJSON = (url) => getText(url).then(JSON.parse);

/* Vega fetches the data files itself, so the same stamp has to be written
   into every data.url inside the spec before handing it over. */
function stampDataUrls(node) {
  if (Array.isArray(node)) {
    node.forEach(stampDataUrls);
  } else if (node && typeof node === "object") {
    if (typeof node.url === "string" && !node.url.includes("v=")) {
      node.url = stamp(node.url);
    }
    Object.values(node).forEach(stampDataUrls);
  }
  return node;
}

/* ---------------------------------------------------------------- charts -- */
const views = [];
let currentFocus = "";
let chooseCouncil = null;   /* set once the council list has loaded */

/* Charts mount as they come into view rather than all fifteen at once. The
   page is around twenty screens tall, and embedding every chart up front
   means fifteen spec fetches, fifteen data fetches and two topojson files
   before anything is interactive. The margin is generous enough that a chart
   is always ready by the time it is scrolled to. */
async function drawCharts() {
  let config = {};
  try {
    config = await getJSON("specs/config.json");
  } catch (err) {
    console.error("Could not load the shared chart config", err);
  }

  /* No action menu. This is a presentation page, and fifteen "..." buttons
     are fifteen pieces of furniture that are not data. Every specification is
     linked from the colophon instead. */
  const options = { actions: false, renderer: "svg", config };

  async function mount(target, spec) {
    try {
      const parsed = stampDataUrls(await getJSON(spec));
      const result = await vegaEmbed(target, parsed, options);
      views.push(result.view);
      /* Vega-Lite turns a spec's `description` into the SVG's aria-label.
         Mirror it onto the container so the card is announced as one image
         rather than as a pile of anonymous paths. */
      if (parsed.description) {
        target.setAttribute("role", "img");
        target.setAttribute("aria-label", parsed.description);
      }
      /* a chart that mounts after the reader has already chosen a council
         still has to show the ring */
      if (currentFocus) applyFocus(result.view, currentFocus);
      /* the hero strip doubles as a picker: clicking a dot chooses that council */
      if (target.id === "vis-finder") {
        result.view.addSignalListener("pick", (_, value) => {
          const name = value && value.Council && value.Council[0];
          if (name && chooseCouncil) chooseCouncil(name);
        });
      }
    } catch (err) {
      target.textContent = "This chart could not be loaded.";
      console.error(`Failed to embed ${spec}`, err);
    }
  }

  const pending = new Map();
  for (const { el, spec } of CHARTS) {
    const target = document.querySelector(el);
    if (target) pending.set(target, spec);
  }

  if (!("IntersectionObserver" in window)) {
    for (const [target, spec] of pending) await mount(target, spec);
    return;
  }

  const io = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const target = entry.target;
      const spec = pending.get(target);
      if (!spec) continue;
      pending.delete(target);
      io.unobserve(target);
      mount(target, spec);
    }
  }, { rootMargin: "800px 0px" });

  for (const target of pending.keys()) io.observe(target);
}

/* -------------------------------------------------------- find a council -- */
const fmt = {
  pct:  (v) => (v === null || isNaN(v) ? "—" : v.toFixed(1) + "%"),
  money:(v) => (v === null || isNaN(v) ? "—" : "$" + Math.round(v)),
  kg:   (v) => (v === null || isNaN(v) ? "—" : v.toFixed(1) + " kg"),
  ord:  (v) => {
    if (v === null || isNaN(v)) return "—";
    const n = Math.round(v), s = ["th", "st", "nd", "rd"], m = n % 100;
    return n + (s[(m - 20) % 10] || s[m] || s[0]);
  }
};

function applyFocus(view, name) {
  try {
    const state = view.getState({ signals: (n) => n === "focusCouncil" });
    if (state.signals.focusCouncil !== undefined) {
      view.signal("focusCouncil", name).run();
    }
  } catch (err) {
    /* a chart without the parameter simply does not take part */
  }
}

function setFocus(name) {
  currentFocus = name;
  for (const view of views) applyFocus(view, name);
}

function paintScorecard(row) {
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  if (!row) {
    set("sc-div", "–");  set("sc-rank", "kept out of landfill");
    set("sc-bins", "–"); set("sc-binsub", "bins offered");
    set("sc-cost", "–"); set("sc-costsub", "to service a garbage bin");
    set("sc-kg", "–");   set("sc-kgsub", "per household, a week");
    set("sb-name", "None chosen");
    set("sb-div", "");
    return;
  }
  set("sc-div", fmt.pct(row.lgprf_diversion_pct));
  set("sc-rank", "kept out of landfill, " + fmt.ord(row.diversion_rank) + " of 79");
  set("sc-bins", String(row.streams));
  set("sc-binsub", "bins: " + row.service_label.toLowerCase());
  set("sc-cost", fmt.money(row.garbage_cost_per_bin));
  set("sc-costsub", "a garbage bin, " + fmt.ord(row.cost_rank) + " cheapest of 79");
  set("sc-kg", fmt.kg(row.kg_per_household_week));
  set("sc-kgsub", "per household, a week");
  set("sb-name", row.Council);
  set("sb-div", fmt.pct(row.lgprf_diversion_pct) + " kept out of landfill");
}

async function wireFinder() {
  let rows;
  try {
    const text = await getText("data/council_snapshot_latest.csv");
    rows = vega.read(text, { type: "csv", parse: "auto" });
  } catch (err) {
    console.error("Could not load the council list", err);
    return;
  }
  rows.sort((a, b) => a.Council.localeCompare(b.Council));
  const byName = new Map(rows.map((r) => [r.Council, r]));

  const selects = [document.getElementById("council-pick"),
                   document.getElementById("council-pick-sticky")].filter(Boolean);

  for (const select of selects) {
    select.innerHTML = "";
    const blank = document.createElement("option");
    blank.value = ""; blank.textContent = "Choose a council…";
    select.appendChild(blank);
    for (const r of rows) {
      const o = document.createElement("option");
      o.value = r.Council; o.textContent = r.Council;
      select.appendChild(o);
    }
    select.addEventListener("change", (e) => chooseCouncil(e.target.value));
  }
  chooseCouncil = (name) => {
    if (name && !byName.has(name)) return;
    for (const other of selects) other.value = name;
    setFocus(name);
    paintScorecard(name ? byName.get(name) : null);
  };
  paintScorecard(null);
}

/* ------------------------------------------------- rail and sticky bar ---- */
function wireChrome() {
  const fill = document.querySelector("#rail i");
  const bar = document.getElementById("stickybar");
  const anchor = document.getElementById("finder");
  let ticking = false;

  const update = () => {
    ticking = false;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (fill) fill.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + "%";
    if (bar && anchor) {
      const past = anchor.getBoundingClientRect().bottom < 0;
      bar.classList.toggle("on", past);
    }
  };
  addEventListener("scroll", () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();
}

(async function run() {
  wireChrome();
  /* the finder no longer waits on the charts: lazy mounting means drawCharts
     returns as soon as the observers are attached */
  await Promise.all([drawCharts(), wireFinder()]);
})();
