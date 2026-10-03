/**
 * JSON bridge for the acceptance suite (tests_acceptance/, REQ 2.8).
 *
 * The Forecast Chart card's logic (auto-detection, editor <-> config mapping, series building)
 * is platform independent TypeScript. The Gherkin scenarios are run by pytest, so this small
 * program exposes that logic over stdin/stdout: it reads one JSON request, writes one JSON
 * response. It is bundled on the fly by tests_acceptance/card_driver.py and is not part of the
 * shipped card.
 */
import fs from "node:fs";
import { normalizeConfig } from "../src/config";
import { describeSource, type States } from "../src/resolve";
import { applyForm, sourceToForm } from "../src/schema";
import { buildSeries } from "../src/series";

const request = JSON.parse(fs.readFileSync(0, "utf8"));
const states = (request.states ?? {}) as States;
const infoFor = (cfg: { entity: string }) =>
  describeSource(cfg as Parameters<typeof describeSource>[0], states[cfg.entity]);

function respond(result: unknown): void {
  process.stdout.write(JSON.stringify(result));
}

switch (request.command) {
  case "form": {
    // what the editor shows for a source (auto-detected values filled in) plus the choices
    const source = normalizeConfig({ sources: [request.source] }).sources[0];
    const info = infoFor(source);
    respond({ form: sourceToForm(source, info), info });
    break;
  }
  case "apply": {
    // the user changed the editor form; returns the new stored config of the source
    const source = normalizeConfig({ sources: [request.source] }).sources[0];
    const prevForm = sourceToForm(source, infoFor(source));
    respond(applyForm(source, prevForm, request.next_form, infoFor));
    break;
  }
  case "series": {
    const config = normalizeConfig(request.config);
    respond(buildSeries(config, states, Date.parse(request.now)));
    break;
  }
  default:
    throw new Error(`unknown command ${request.command}`);
}
