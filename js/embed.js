/* Embed every chart. One entry per spec; add a line as each chart is built. */

const CHARTS = [
  { el: "#vis-03-choropleth", spec: "specs/03-choropleth-diversion.vl.json" }

  // Still to build — see Research/04-chart-plan.md
  // { el: "#vis-01-waffle",      spec: "specs/01-waffle-streams.vl.json" },
  // { el: "#vis-02-streamgraph", spec: "specs/02-streamgraph-history.vl.json" },
  // { el: "#vis-04-beeswarm",    spec: "specs/04-beeswarm-groups.vl.json" },
  // { el: "#vis-05-rollout",     spec: "specs/05-rollout-smallmultiples.vl.json" },
  // { el: "#vis-06-ridgeline",   spec: "specs/06-ridgeline-bincount.vl.json" },
  // { el: "#vis-07-nogreenbin",  spec: "specs/07-nogreenbin-map.vl.json" },
  // { el: "#vis-08-heatmap",     spec: "specs/08-heatmap-councils.vl.json" },
  // { el: "#vis-09-trajectory",  spec: "specs/09-cost-diversion-path.vl.json" },
  // { el: "#vis-10-costmap",     spec: "specs/10-cost-symbolmap.vl.json" },
  // { el: "#vis-11-parallel",    spec: "specs/11-parallel-coordinates.vl.json" },
  // { el: "#vis-12-facilities",  spec: "specs/12-facilities-connection.vl.json" }
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
