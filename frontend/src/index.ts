import { CARD_TYPE, EDITOR_TYPE } from "./config";
import { ForecastChartCard } from "./card";
import { ForecastChartCardEditor } from "./editor";

if (!customElements.get(CARD_TYPE)) customElements.define(CARD_TYPE, ForecastChartCard);
if (!customElements.get(EDITOR_TYPE)) customElements.define(EDITOR_TYPE, ForecastChartCardEditor);

declare global {
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === CARD_TYPE)) {
  window.customCards.push({
    type: CARD_TYPE,
    name: "Forecast Chart",
    description:
      "Plots forecast list attributes (e.g. Template Forecast, HAEO, EPEX Spot) as a time series.",
    preview: true,
    documentationURL: "https://github.com/principat/ha-template-forecast",
  });
}
