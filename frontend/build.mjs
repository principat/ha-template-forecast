// Bundles the card into one ES module that the integration serves as a static file.
import { build } from "esbuild";

const OUT = "../custom_components/template_forecast/www/forecast-chart-card.js";

await build({
  entryPoints: ["src/index.ts"],
  bundle: true,
  minify: true,
  format: "esm",
  target: "es2022",
  platform: "browser",
  outfile: OUT,
  legalComments: "none",
  logLevel: "info",
});
