/* Embed every chart.

   Titles and captions live in index.html so the page controls typography;
   the specs carry only the graphic.

   BUILD is appended to every spec and data request. Browsers cache those
   fetches hard and a normal reload does not clear them, so without this a
   visitor can sit on a stale chart indefinitely. Bump it when specs or data
   change. */

const BUILD = "2026-10-11f";

const CHARTS = [
  { el: "#vis-01-waffle",       spec: "specs/01-waffle-streams.vl.json" },
  { el: "#vis-02-mosaic",       spec: "specs/02-mosaic-volume-composition.vl.json" },
  { el: "#vis-03-kghousehold",  spec: "specs/03-choropleth-kg-household.vl.json" },
  { el: "#vis-04-choropleth",   spec: "specs/03-choropleth-diversion.vl.json" },
  { el: "#vis-05-beeswarm",     spec: "specs/05-beeswarm-groups.vl.json" },
  { el: "#vis-06-slope",        spec: "specs/06-slope-not-recovered.vl.json" },
  { el: "#vis-07-density",      spec: "specs/07-density-bincount.vl.json" },
  { el: "#vis-08-nogreenbin",   spec: "specs/08-nogreenbin-map.vl.json" },
  { el: "#vis-09-trajectory",   spec: "specs/09-cost-diversion-path.vl.json" },
  { el: "#vis-10-dorling",      spec: "specs/10-cost-dorling.vl.json" },
  { el: "#vis-11-bivariate",    spec: "specs/11-bivariate-seifa-diversion.vl.json" },
  { el: "#vis-12-seifaservice", spec: "specs/12-seifa-by-service.vl.json" },
  { el: "#vis-13-streamgraph",  spec: "specs/13-streamgraph-history.vl.json" },
  { el: "#vis-14-rollout",      spec: "specs/14-rollout-smallmultiples.vl.json" }
];

const stamp = (url) => url + (url.includes("?") ? "&" : "?") + "v=" + BUILD;

const getJSON = (url) =>
  fetch(stamp(url), { cache: "no-cache" }).then((r) => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  });

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

async function run() {
  let config = {};
  try {
    config = await getJSON("specs/config.json");
  } catch (err) {
    console.error("Could not load the shared chart config", err);
  }

  const options = {
    actions: { export: true, source: true, compiled: false, editor: true },
    renderer: "svg",
    config
  };

  for (const { el, spec } of CHARTS) {
    const target = document.querySelector(el);
    if (!target) continue;
    try {
      await vegaEmbed(el, stampDataUrls(await getJSON(spec)), options);
    } catch (err) {
      target.textContent = "This chart could not be loaded.";
      console.error(`Failed to embed ${spec}`, err);
    }
  }
}

run();
