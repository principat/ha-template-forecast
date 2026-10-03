import type { SourceConfig } from "./config";
import {
  listAttributes,
  numericKeys,
  pickListAttribute,
  pickTimeKey,
  pickValueKey,
  timeKeys,
} from "./detect";

export interface StateLike {
  state: string;
  attributes: Record<string, unknown>;
}

export type States = Record<string, StateLike | undefined>;

/** What is available on an entity and what the auto-detection would choose. */
export interface SourceInfo {
  listAttributes: string[];
  attribute?: string;
  timeKeys: string[];
  timeKey?: string;
  numericKeys: string[];
  valueKey?: string;
}

/**
 * Looks at an entity state and the (possibly partial) source config and returns the available
 * choices plus the effective selection (configured value if valid, otherwise auto-detected).
 */
export function describeSource(cfg: SourceConfig, state: StateLike | undefined): SourceInfo {
  const attrs = state?.attributes;
  const candidates = listAttributes(attrs);
  const hint = typeof attrs?.target_attribute === "string" ? attrs.target_attribute : undefined;
  const attribute =
    cfg.attribute && candidates.includes(cfg.attribute)
      ? cfg.attribute
      : cfg.attribute && attrs && Array.isArray(attrs[cfg.attribute])
        ? cfg.attribute
        : pickListAttribute(candidates, hint);
  const list = attribute && attrs ? attrs[attribute] : undefined;
  const tKeys = timeKeys(list);
  const timeKey = cfg.time_key && tKeys.includes(cfg.time_key) ? cfg.time_key : pickTimeKey(tKeys);
  const nKeys = numericKeys(list, timeKey ? [timeKey] : []);
  const configured = cfg.values?.[0]?.key;
  const valueKey = configured && nKeys.includes(configured) ? configured : pickValueKey(nKeys);
  return {
    listAttributes: candidates,
    attribute,
    timeKeys: tKeys,
    timeKey: cfg.time_key ?? timeKey,
    numericKeys: nKeys,
    valueKey,
  };
}
