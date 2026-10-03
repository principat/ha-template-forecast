import { LitElement, html, nothing, type TemplateResult } from "lit";
import Plotly from "plotly.js-basic-dist-min";
import { listAttributes } from "./detect";
import { CARD_TYPE, DEFAULTS, EDITOR_TYPE, normalizeConfig, type CardConfig } from "./config";
import { buildFigure } from "./figure";
import { translator } from "./i18n";
import type { States } from "./resolve";
import { buildSeries, type SeriesError } from "./series";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Hass = any;

/**
 * The card renders into the light DOM on purpose: Plotly injects its stylesheet (modebar,
 * hover labels, ...) into document.head, which would not reach a shadow root.
 */
export class ForecastChartCard extends LitElement {
  static properties = {
    _config: { state: true },
    _errors: { state: true },
  };

  declare _config?: CardConfig;
  declare _errors: SeriesError[];

  private _hass?: Hass;
  private _signature = "";
  private _resizeObserver?: ResizeObserver;
  private _plotted = false;

  constructor() {
    super();
    this._errors = [];
  }

  createRenderRoot(): HTMLElement {
    return this;
  }

  static getConfigElement(): HTMLElement {
    return document.createElement(EDITOR_TYPE);
  }

  static getStubConfig(hass: Hass): Partial<CardConfig> {
    const states = (hass?.states ?? {}) as States;
    const candidates = Object.keys(states).filter(
      (id) => listAttributes(states[id]?.attributes).length > 0,
    );
    const preferred =
      candidates.find((id) => listAttributes(states[id]?.attributes).includes("forecast")) ??
      candidates[0];
    return { sources: preferred ? [{ entity: preferred }] : [] };
  }

  setConfig(config: unknown): void {
    this._config = normalizeConfig(config);
    this._signature = "";
    this.requestUpdate();
  }

  set hass(hass: Hass) {
    this._hass = hass;
    const sig = this._computeSignature(hass);
    if (sig !== this._signature) {
      this._signature = sig;
      this.requestUpdate();
    }
  }

  get hass(): Hass {
    return this._hass;
  }

  getCardSize(): number {
    return Math.ceil((this._config?.height ?? DEFAULTS.height) / 50);
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 6, min_rows: 3 };
  }

  /** Re-render only when a relevant state object, the theme or the language changed. */
  private _computeSignature(hass: Hass): string {
    if (!this._config || !hass) return "";
    const states = hass.states ?? {};
    const parts = this._config.sources.map((s) => {
      const st = states[s.entity];
      return st ? `${st.last_updated}|${st.last_changed}` : "-";
    });
    return [parts.join(","), hass.themes?.darkMode, hass.language, hass.config?.time_zone].join(
      "#",
    );
  }

  protected render(): TemplateResult {
    const t = translator(this._hass?.language);
    const cfg = this._config;
    const height = cfg?.height ?? DEFAULTS.height;
    const empty = !cfg || !cfg.sources.some((s) => s.entity);
    return html`
      <ha-card .header=${cfg?.title || nothing}>
        <div class="tfc-body" style="padding: 8px 16px 16px;">
          ${empty ? html`<div class="tfc-empty">${t("empty")}</div>` : nothing}
          <div class="tfc-plot" style="height:${height}px;${empty ? "display:none;" : ""}"></div>
          ${this._errors.map(
            (e) =>
              html`<div class="tfc-error" style="color: var(--error-color, #db4437);">
                ${e.entity}: ${t(e.code)}${e.detail ? ` (${e.detail})` : ""}
              </div>`,
          )}
        </div>
      </ha-card>
    `;
  }

  protected updated(): void {
    this._draw();
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => {
      const plot = this.querySelector<HTMLElement>(".tfc-plot");
      if (plot && this._plotted) Plotly.Plots.resize(plot);
    });
    this._resizeObserver.observe(this);
    // Re-attached cards (dashboard edit mode) lost their plot
    this._signature = "";
    if (this._hass) this.hass = this._hass;
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    const plot = this.querySelector<HTMLElement>(".tfc-plot");
    if (plot && this._plotted) Plotly.purge(plot);
    this._plotted = false;
  }

  private _draw(): void {
    const cfg = this._config;
    const hass = this._hass;
    const plot = this.querySelector<HTMLElement>(".tfc-plot");
    if (!cfg || !hass || !plot) return;
    if (!cfg.sources.some((s) => s.entity)) {
      if (this._errors.length) this._errors = [];
      return;
    }
    const now = Date.now();
    const result = buildSeries(cfg, hass.states as States, now);
    const style = getComputedStyle(this);
    const theme = {
      text: style.getPropertyValue("--primary-text-color").trim() || "#888",
      grid: style.getPropertyValue("--divider-color").trim() || "rgba(128,128,128,0.3)",
    };
    const tz = hass.config?.time_zone || Intl.DateTimeFormat().resolvedOptions().timeZone;
    const fig = buildFigure(result, cfg, theme, tz, now);
    Plotly.react(plot, fig.data, fig.layout, {
      responsive: true,
      displaylogo: false,
      displayModeBar: false,
    });
    this._plotted = true;

    const same =
      this._errors.length === result.errors.length &&
      this._errors.every(
        (e, i) =>
          e.entity === result.errors[i].entity &&
          e.code === result.errors[i].code &&
          e.detail === result.errors[i].detail,
      );
    if (!same) this._errors = result.errors;
  }
}

export const CARD_ELEMENT = CARD_TYPE;
