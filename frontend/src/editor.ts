import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { DEFAULTS, normalizeConfig, type CardConfig, type SourceConfig } from "./config";
import { listAttributes } from "./detect";
import { translator } from "./i18n";
import { describeSource, type States } from "./resolve";
import {
  applyForm,
  buildGlobalSchema,
  buildSourceSchema,
  sourceToForm,
  type Schema,
} from "./schema";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Hass = any;

/**
 * Home Assistant loads `ha-form` lazily. Inside the card edit dialog it is normally there
 * already; if not, borrowing the config element of a built-in card makes HA load it.
 */
async function loadHaForm(): Promise<void> {
  if (customElements.get("ha-form")) return;
  try {
    const helpers = await (window as unknown as { loadCardHelpers?: () => Promise<Hass> })
      .loadCardHelpers?.();
    const card = await helpers?.createCardElement({ type: "entities", entities: [] });
    await card?.constructor?.getConfigElement?.();
  } catch {
    // nothing else to try; the editor then stays empty and the YAML editor still works
  }
}

/**
 * Visual editor. It always starts from the stored config (`setConfig`), so an existing card can
 * be reopened and changed at any time; auto-detection only runs when the user picks a new
 * entity or list attribute, never on already configured values.
 */
export class ForecastChartCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  declare hass: Hass;
  declare _config?: CardConfig;

  private _entityIds?: string[];

  connectedCallback(): void {
    super.connectedCallback();
    void loadHaForm().then(() => this.requestUpdate());
  }

  setConfig(config: unknown): void {
    this._config = normalizeConfig(config);
  }

  private get _t() {
    return translator(this.hass?.language);
  }

  /** Entities that have at least one list attribute (cached: scanning all states is costly). */
  private _entities(): string[] | undefined {
    if (this._entityIds) return this._entityIds;
    const states = this.hass?.states as States | undefined;
    if (!states) return undefined;
    this._entityIds = Object.keys(states).filter(
      (id) => listAttributes(states[id]?.attributes).length > 0,
    );
    return this._entityIds;
  }

  private _emit(config: CardConfig): void {
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }),
    );
  }

  private _info(cfg: SourceConfig) {
    return describeSource(cfg, (this.hass?.states as States | undefined)?.[cfg.entity]);
  }

  private _globalChanged(ev: CustomEvent): void {
    if (!this._config) return;
    const v = ev.detail.value as Record<string, unknown>;
    const next: CardConfig = { ...this._config, sources: this._config.sources };
    for (const key of ["title", "height", "time_range", "show_now", "show_legend"] as const) {
      if (v[key] === undefined || v[key] === "") delete next[key];
      else (next as unknown as Record<string, unknown>)[key] = v[key];
    }
    this._emit(next);
  }

  private _sourceChanged(index: number, ev: CustomEvent): void {
    if (!this._config) return;
    const prev = this._config.sources[index];
    const prevForm = sourceToForm(prev, this._info(prev));
    const updated = applyForm(prev, prevForm, ev.detail.value, (cfg) => this._info(cfg));
    this._setSources(this._config.sources.map((s, i) => (i === index ? updated : s)));
  }

  private _setSources(sources: SourceConfig[]): void {
    if (this._config) this._emit({ ...this._config, sources });
  }

  private _move(index: number, delta: number): void {
    if (!this._config) return;
    const sources = [...this._config.sources];
    const target = index + delta;
    if (target < 0 || target >= sources.length) return;
    [sources[index], sources[target]] = [sources[target], sources[index]];
    this._setSources(sources);
  }

  private _remove(index: number): void {
    if (!this._config) return;
    this._setSources(this._config.sources.filter((_, i) => i !== index));
  }

  private _add(): void {
    if (!this._config) return;
    this._setSources([...this._config.sources, { entity: "" }]);
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) return nothing;
    const t = this._t;
    const cfg = this._config;
    const label = (s: { name?: string }) => t(s.name ?? "");
    const globalData = {
      title: cfg.title ?? "",
      height: cfg.height ?? DEFAULTS.height,
      time_range: cfg.time_range ?? DEFAULTS.time_range,
      show_now: cfg.show_now ?? DEFAULTS.show_now,
      show_legend: cfg.show_legend ?? DEFAULTS.show_legend,
    };
    return html`
      <ha-form
        .hass=${this.hass}
        .data=${globalData}
        .schema=${buildGlobalSchema(t)}
        .computeLabel=${label}
        @value-changed=${this._globalChanged}
      ></ha-form>
      <h3>${t("sources")}</h3>
      ${cfg.sources.map((src, i) => this._renderSource(src, i, label))}
      <button class="add" @click=${this._add}>＋ ${t("add_source")}</button>
    `;
  }

  private _renderSource(
    src: SourceConfig,
    index: number,
    label: (s: { name?: string }) => string,
  ): TemplateResult {
    const t = this._t;
    const info = this._info(src);
    const form = sourceToForm(src, info);
    const schema: Schema = buildSourceSchema(form, info, this._entities(), t);
    const last = this._config!.sources.length - 1;
    return html`
      <div class="source">
        <div class="head">
          <span class="title">${index + 1}. ${src.entity || t("pick_entity")}</span>
          <button title=${t("move_up")} ?disabled=${index === 0} @click=${() => this._move(index, -1)}>
            ↑
          </button>
          <button
            title=${t("move_down")}
            ?disabled=${index === last}
            @click=${() => this._move(index, 1)}
          >
            ↓
          </button>
          <button title=${t("remove")} @click=${() => this._remove(index)}>✕</button>
        </div>
        <ha-form
          .hass=${this.hass}
          .data=${form}
          .schema=${schema}
          .computeLabel=${label}
          @value-changed=${(ev: CustomEvent) => this._sourceChanged(index, ev)}
        ></ha-form>
      </div>
    `;
  }

  static styles = css`
    :host {
      display: block;
    }
    h3 {
      margin: 16px 0 8px;
    }
    .source {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 8px 12px;
      margin-bottom: 12px;
    }
    .head {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 8px;
    }
    .title {
      flex: 1;
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    button {
      cursor: pointer;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      background: var(--card-background-color);
      color: var(--primary-text-color);
      padding: 4px 10px;
      font: inherit;
    }
    button[disabled] {
      opacity: 0.4;
      cursor: default;
    }
    .add {
      width: 100%;
      padding: 8px;
    }
  `;
}
