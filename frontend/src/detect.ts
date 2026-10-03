/**
 * Auto-detection helpers. Pure functions, no DOM / Home Assistant dependency.
 * They answer: which attribute holds the series, which key is the time, which keys are values.
 */

export type Entry = Record<string, unknown>;

const SAMPLE = 25;
const PREFERRED_LIST_ATTRIBUTES = ["forecast", "data"];
const PREFERRED_TIME_KEYS = ["time", "start_time", "datetime", "start", "timestamp"];
const ISO_LIKE = /^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$/;
const NUMERIC_STRING = /^-?\d+(\.\d+)?([eE][+-]?\d+)?$/;

const isRecord = (v: unknown): v is Entry =>
  !!v && typeof v === "object" && !Array.isArray(v) && !(v instanceof Date);

/** Attributes whose value is a non-empty list of objects. */
export function listAttributes(attributes: Record<string, unknown> | undefined): string[] {
  if (!attributes) return [];
  return Object.entries(attributes)
    .filter(([, v]) => Array.isArray(v) && v.length > 0 && v.some(isRecord))
    .map(([k]) => k);
}

/**
 * Default list attribute: `forecast`, then the configured target attribute (hint), then `data`,
 * then the first candidate.
 */
export function pickListAttribute(candidates: string[], hint?: string): string | undefined {
  const order = [PREFERRED_LIST_ATTRIBUTES[0], hint, ...PREFERRED_LIST_ATTRIBUTES.slice(1)];
  for (const name of order) {
    if (name && candidates.includes(name)) return name;
  }
  return candidates[0];
}

/** Union of keys of the first entries, in order of first appearance. */
export function entryKeys(list: unknown): string[] {
  if (!Array.isArray(list)) return [];
  const keys: string[] = [];
  for (const entry of list.slice(0, SAMPLE)) {
    if (!isRecord(entry)) continue;
    for (const k of Object.keys(entry)) if (!keys.includes(k)) keys.push(k);
  }
  return keys;
}

function samples(list: unknown, key: string): unknown[] {
  if (!Array.isArray(list)) return [];
  return list
    .slice(0, SAMPLE)
    .filter(isRecord)
    .map((e) => e[key])
    .filter((v) => v !== undefined && v !== null);
}

/** Parses a timestamp (Date, ISO string, unix seconds / milliseconds) to epoch milliseconds. */
export function parseTime(v: unknown): number | null {
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v.getTime();
  if (typeof v === "number" && Number.isFinite(v)) return v < 1e11 ? v * 1000 : v;
  if (typeof v === "string" && ISO_LIKE.test(v.trim())) {
    const ms = Date.parse(v.trim().replace(" ", "T"));
    return Number.isNaN(ms) ? null : ms;
  }
  return null;
}

/**
 * Keys that look like a timestamp. Strings must be ISO-8601; plain numbers only count when the
 * key has a well-known time name (otherwise every numeric value would look like a timestamp).
 */
export function timeKeys(list: unknown): string[] {
  return entryKeys(list).filter((key) => {
    const vals = samples(list, key);
    if (!vals.length) return false;
    const knownName = PREFERRED_TIME_KEYS.includes(key);
    return vals.every((v) =>
      typeof v === "number" ? knownName && parseTime(v) !== null : parseTime(v) !== null,
    );
  });
}

export function pickTimeKey(keys: string[]): string | undefined {
  for (const name of PREFERRED_TIME_KEYS) if (keys.includes(name)) return name;
  return keys[0];
}

export function toNumber(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v === "string" && NUMERIC_STRING.test(v.trim())) return Number(v);
  return null;
}

/**
 * Keys with numeric values (numbers or numeric strings), excluding the given keys. A key still
 * counts when a minority of entries is not numeric (e.g. a single "unknown" in a series).
 */
export function numericKeys(list: unknown, exclude: string[] = []): string[] {
  return entryKeys(list).filter((key) => {
    if (exclude.includes(key)) return false;
    const vals = samples(list, key);
    const numeric = vals.filter((v) => toNumber(v) !== null).length;
    return numeric > 0 && numeric >= vals.length / 2;
  });
}

export function pickValueKey(keys: string[]): string | undefined {
  return keys.includes("value") ? "value" : keys[0];
}
