import { DEFAULTS, type Axis, type CardConfig, type Shape, type ValueConfig } from "./config";
import { entryKeys, parseTime, toNumber } from "./detect";
import { describeSource, type States } from "./resolve";

/** Tableau-10 style palette; readable on light and dark backgrounds. */
export const PALETTE = [
  "#4C78A8",
  "#F58518",
  "#54A24B",
  "#E45756",
  "#72B7B2",
  "#B279A2",
  "#FF9DA6",
  "#9D755D",
  "#EECA3B",
  "#BAB0AC",
];

export type ErrorCode =
  | "entity_missing"
  | "entity_unavailable"
  | "attribute_missing"
  | "time_missing"
  | "value_missing"
  | "no_data";

export interface SeriesError {
  entity: string;
  code: ErrorCode;
  detail?: string;
}

export interface Series {
  entity: string;
  key: string;
  name: string;
  color: string;
  unit: string;
  axis: "left" | "right";
  /** configured axis; "auto" is resolved by assignAxes */
  axisSetting: Axis;
  shape: Shape;
  visible: boolean;
  /** epoch milliseconds, ascending */
  t: number[];
  y: number[];
}

export interface SeriesResult {
  series: Series[];
  errors: SeriesError[];
}

const cleanUnit = (u: string) => u.replace(/[{}]/g, "");

function friendlyName(entity: string, states: States): string {
  const n = states[entity]?.attributes?.friendly_name;
  return typeof n === "string" && n ? n : entity;
}

/** Applies `from_now`: keep the entry that is active right now plus everything after it. */
function fromNow(t: number[], y: number[], now: number): [number[], number[]] {
  let start = 0;
  for (let i = 0; i < t.length; i++) {
    if (t[i] <= now) start = i;
    else break;
  }
  return [t.slice(start), y.slice(start)];
}

export function buildSeries(config: CardConfig, states: States, now: number): SeriesResult {
  const series: Series[] = [];
  const errors: SeriesError[] = [];
  let colorIndex = 0;

  for (const source of config.sources) {
    const entity = source.entity;
    if (!entity) continue;
    const state = states[entity];
    if (!state) {
      errors.push({ entity, code: "entity_missing" });
      continue;
    }
    const info = describeSource(source, state);
    const attribute = source.attribute ?? info.attribute;
    const list = attribute ? state.attributes[attribute] : undefined;
    if (!attribute || !Array.isArray(list)) {
      errors.push({
        entity,
        code: state.state === "unavailable" ? "entity_unavailable" : "attribute_missing",
        detail: attribute,
      });
      continue;
    }
    const timeKey = source.time_key ?? info.timeKey;
    if (!timeKey || !entryKeys(list).includes(timeKey)) {
      errors.push({ entity, code: "time_missing", detail: timeKey });
      continue;
    }
    const values: ValueConfig[] =
      source.values && source.values.length
        ? source.values
        : info.valueKey
          ? [{ key: info.valueKey }]
          : [];
    if (!values.length) {
      errors.push({ entity, code: "value_missing" });
      continue;
    }

    const baseName = friendlyName(entity, states);
    const entityUnit =
      typeof state.attributes.unit_of_measurement === "string"
        ? state.attributes.unit_of_measurement
        : "";

    values.forEach((vc, i) => {
      const factor = vc.factor ?? DEFAULTS.factor;
      const offset = vc.offset ?? DEFAULTS.offset;
      let pairs: Array<[number, number]> = [];
      for (const entry of list) {
        if (!entry || typeof entry !== "object") continue;
        const rec = entry as Record<string, unknown>;
        const ts = parseTime(rec[timeKey]);
        const num = toNumber(rec[vc.key]);
        if (ts === null || num === null) continue;
        pairs.push([ts, num * factor + offset]);
      }
      pairs.sort((a, b) => a[0] - b[0]);
      let t = pairs.map((p) => p[0]);
      let y = pairs.map((p) => p[1]);
      if ((config.time_range ?? DEFAULTS.time_range) === "from_now") [t, y] = fromNow(t, y, now);
      if (!t.length) {
        errors.push({ entity, code: "no_data", detail: vc.key });
        return;
      }
      // Only the primary field of a source takes the entity unit by default; attribute fields
      // like outdoor_temp have their own unit that we cannot know.
      const unit = cleanUnit(vc.unit ?? (i === 0 ? entityUnit : ""));
      series.push({
        entity,
        key: vc.key,
        name: vc.name ?? (values.length > 1 ? `${baseName} – ${vc.key}` : baseName),
        color: vc.color ?? PALETTE[colorIndex % PALETTE.length],
        unit,
        axis: "left",
        axisSetting: vc.axis ?? DEFAULTS.axis,
        shape: vc.shape ?? DEFAULTS.shape,
        visible: vc.visible ?? DEFAULTS.visible,
        t,
        y,
      });
      colorIndex++;
    });
  }

  assignAxes(series);
  return { series, errors };
}

/**
 * `auto` axis: the first unit goes left, every different unit goes right. Explicit left/right
 * settings win. (Only two axes are supported; further units share the right one.)
 */
function assignAxes(series: Series[]): void {
  let leftUnit: string | undefined;
  for (const s of series) {
    if (s.axisSetting === "left" || s.axisSetting === "right") {
      s.axis = s.axisSetting;
      if (s.axis === "left" && leftUnit === undefined) leftUnit = s.unit;
    } else if (leftUnit === undefined) {
      leftUnit = s.unit;
      s.axis = "left";
    } else {
      s.axis = s.unit === leftUnit ? "left" : "right";
    }
  }
}
