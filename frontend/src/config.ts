export const CARD_TYPE = "forecast-chart-card";
export const EDITOR_TYPE = "forecast-chart-card-editor";

export type Shape = "hv" | "linear";
export type Axis = "auto" | "left" | "right";
export type TimeRange = "all" | "from_now";

/** One plotted line: a key inside the list entries of a source. */
export interface ValueConfig {
  key: string;
  name?: string;
  color?: string;
  factor?: number;
  offset?: number;
  unit?: string;
  shape?: Shape;
  axis?: Axis;
  visible?: boolean;
}

/** One entity + list attribute. Everything except `entity` is auto-detected when omitted. */
export interface SourceConfig {
  entity: string;
  attribute?: string;
  time_key?: string;
  values?: ValueConfig[];
}

export interface CardConfig {
  type: string;
  title?: string;
  height?: number;
  time_range?: TimeRange;
  show_now?: boolean;
  show_legend?: boolean;
  sources: SourceConfig[];
}

const finite = (v: unknown): number | undefined =>
  typeof v === "number" && Number.isFinite(v) ? v : undefined;

const str = (v: unknown): string | undefined =>
  typeof v === "string" && v !== "" ? v : undefined;

function normalizeValue(raw: unknown): ValueConfig | undefined {
  if (typeof raw === "string" && raw) return { key: raw };
  if (!raw || typeof raw !== "object") return undefined;
  const r = raw as Record<string, unknown>;
  const key = str(r.key);
  if (!key) return undefined;
  const out: ValueConfig = { key };
  const name = str(r.name);
  if (name) out.name = name;
  const color = str(r.color);
  if (color) out.color = color;
  const factor = finite(r.factor);
  if (factor !== undefined) out.factor = factor;
  const offset = finite(r.offset);
  if (offset !== undefined) out.offset = offset;
  const unit = typeof r.unit === "string" ? r.unit : undefined;
  if (unit !== undefined) out.unit = unit;
  if (r.shape === "hv" || r.shape === "linear") out.shape = r.shape;
  if (r.axis === "auto" || r.axis === "left" || r.axis === "right") out.axis = r.axis;
  if (typeof r.visible === "boolean") out.visible = r.visible;
  return out;
}

function normalizeSource(raw: unknown): SourceConfig {
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const out: SourceConfig = { entity: typeof r.entity === "string" ? r.entity : "" };
  const attribute = str(r.attribute);
  if (attribute) out.attribute = attribute;
  const timeKey = str(r.time_key);
  if (timeKey) out.time_key = timeKey;
  if (Array.isArray(r.values)) {
    const values = r.values.map(normalizeValue).filter((v): v is ValueConfig => !!v);
    if (values.length) out.values = values;
  }
  return out;
}

/** Validates and cleans a raw (YAML) card config. Unknown keys are dropped. */
export function normalizeConfig(raw: unknown): CardConfig {
  if (!raw || typeof raw !== "object") throw new Error("Invalid configuration");
  const r = raw as Record<string, unknown>;
  if (r.sources !== undefined && !Array.isArray(r.sources)) {
    throw new Error("'sources' must be a list");
  }
  const cfg: CardConfig = {
    type: typeof r.type === "string" ? r.type : `custom:${CARD_TYPE}`,
    sources: ((r.sources as unknown[]) ?? []).map(normalizeSource),
  };
  const title = typeof r.title === "string" ? r.title : undefined;
  if (title !== undefined) cfg.title = title;
  const height = finite(r.height);
  if (height !== undefined && height > 0) cfg.height = height;
  if (r.time_range === "all" || r.time_range === "from_now") cfg.time_range = r.time_range;
  if (typeof r.show_now === "boolean") cfg.show_now = r.show_now;
  if (typeof r.show_legend === "boolean") cfg.show_legend = r.show_legend;
  return cfg;
}

export const DEFAULTS = {
  height: 320,
  time_range: "all" as TimeRange,
  show_now: true,
  show_legend: true,
  factor: 1,
  offset: 0,
  shape: "hv" as Shape,
  axis: "auto" as Axis,
  visible: true,
};
