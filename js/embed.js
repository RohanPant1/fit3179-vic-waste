/* Embed every chart. One entry per spec. */

const CHARTS = [
  { el: "#vis-01-waffle",      spec: "specs/01-waffle-streams.vl.json" },
  { el: "#vis-02-mosaic",      spec: "specs/02-mosaic-volume-composition.vl.json" },
  { el: "#vis-03-kghousehold", spec: "specs/03-choropleth-kg-household.vl.json" },
  { el: "#vis-04-choropleth",  spec: "specs/03-choropleth-diversion.vl.json" },
  { el: "#vis-05-beeswarm",    spec: "specs/05-beeswarm-groups.vl.json" },
  { el: "#vis-06-slope",       spec: "specs/06-slope-not-recovered.vl.json" },
  { el: "#vis-07-density",     spec: "specs/07-density-bincount.vl.json" },
  { el: "#vis-08-nogreenbin",  spec: "specs/08-nogreenbin-map.vl.json" },
  { el: "#vis-09-trajectory",  spec: "specs/09-cost-diversion-path.vl.json" },
  { el: "#vis-10-costmap",     spec: "specs/10-cost-symbolmap.vl.json" },
  { el: "#vis-11-bivariate",   spec: "specs/11-bivariate-seifa-diversion.vl.json" },
  { el: "#vis-12-seifaservice",spec: "specs/12-seifa-by-service.vl.json" },
  { el: "#vis-13-streamgraph", spec: "specs/13-streamgraph-history.vl.json" },
  { el: "#vis-14-rollout",     spec: "specs/14-rollout-smallmultiples.vl.json" }
];

// Shared theme, so every chart matches the page typography.
async function run() {
  const config = await fetch("specs/config.json").then((r) => r.json());

  const options = {
    actions: { export: true, source: true, compiled: false, editor: true },
    renderer: "svg",
    config
  };

  for (const { el, spec } of CHARTS) {
    const target = document.querySelector(el);
    if (!target) continue;
    try {
      await vegaEmbed(el, spec, options);
    } catch (err) {
      target.textContent = "This chart could not be loaded.";
      console.error(`Failed to embed ${spec}`, err);
    }
  }
}

run();
