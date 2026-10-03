/**
 * Mapping between the YAML card config and the flat form data used by the editor (`ha-form`),
 * plus the form schema. Pure functions so they can be tested without a browser.
 */
import type { SourceConfig, ValueConfig } from "./config";
import type { Translate } from "./i18n";
import type { SourceInfo } from "./resolve";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type FormData = Record<string, any>;

export function hexToRgb(hex: string | undefined): [number, number, number] | undefined {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex ?? "");
  if (!m) return undefined;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function rgbToHex(rgb: unknown): string | undefined {
  if (!Array.isArray(rgb) || rgb.length !== 3) return undefined;
  return (
    "#" +
    rgb
      .map((c) => Math.max(0, Math.min(255, Math.round(Number(c)))).toString(16).padStart(2, "0"))
      .join("")
  );
}

/** Keys currently plotted for a source, primary first. */
export function plottedKeys(src: SourceConfig, info: SourceInfo): string[] {
  if (src.values?.length) return src.values.map((v) => v.key);
  return info.valueKey ? [info.valueKey] : [];
}

function valueToDetail(v: ValueConfig | undefined): FormData {
  return {
    name: v?.name ?? "",
    color: hexToRgb(v?.color),
    factor: v?.factor ?? 1,
    offset: v?.offset ?? 0,
    unit: v?.unit ?? "",
    shape: v?.shape ?? "hv",
    axis: v?.axis ?? "auto",
    visible: v?.visible ?? true,
  };
}

function detailToValue(key: string, d: FormData | undefined): ValueConfig {
  const v: ValueConfig = { key };
  if (!d) return v;
  if (typeof d.name === "string" && d.name) v.name = d.name;
  const color = rgbToHex(d.color);
  if (color) v.color = color;
  if (typeof d.factor === "number" && Number.isFinite(d.factor) && d.factor !== 1) {
    v.factor = d.factor;
  }
  if (typeof d.offset === "number" && Number.isFinite(d.offset) && d.offset !== 0) {
    v.offset = d.offset;
  }
  if (typeof d.unit === "string" && d.unit) v.unit = d.unit;
  if (d.shape === "linear") v.shape = "linear";
  if (d.axis === "left" || d.axis === "right") v.axis = d.axis;
  if (d.visible === false) v.visible = false;
  return v;
}

/** Config -> form data. Auto-detected values are filled in so the dropdowns show them. */
export function sourceToForm(src: SourceConfig, info: SourceInfo): FormData {
  const keys = plottedKeys(src, info);
  const form: FormData = {
    entity: src.entity,
    attribute: src.attribute ?? info.attribute ?? "",
    time_key: src.time_key ?? info.timeKey ?? "",
    value_key: keys[0] ?? "",
    extra_keys: keys.slice(1),
  };
  keys.forEach((key, i) => {
    form[`detail_${i}`] = valueToDetail(src.values?.find((v) => v.key === key));
  });
  return form;
}

function detected(base: SourceConfig, info: SourceInfo): SourceConfig {
  const out: SourceConfig = { entity: base.entity };
  if (info.attribute) out.attribute = info.attribute;
  if (info.timeKey) out.time_key = info.timeKey;
  if (info.valueKey) out.values = [{ key: info.valueKey }];
  return out;
}

/**
 * Form data -> config. Changing the entity or the list attribute re-runs the auto-detection
 * (time field, value field, no extra fields); all other changes are taken over as entered.
 */
export function applyForm(
  prev: SourceConfig,
  prevForm: FormData,
  next: FormData,
  infoFor: (cfg: SourceConfig) => SourceInfo,
): SourceConfig {
  if (next.entity !== prevForm.entity) {
    const base: SourceConfig = { entity: next.entity ?? "" };
    return detected(base, infoFor(base));
  }
  if (next.attribute !== prevForm.attribute) {
    const base: SourceConfig = { entity: next.entity, attribute: next.attribute };
    return detected(base, infoFor(base));
  }
  const prevKeys: string[] = [prevForm.value_key, ...(prevForm.extra_keys ?? [])].filter(Boolean);
  const keys: string[] = [next.value_key, ...(next.extra_keys ?? [])].filter(
    (k, i, all) => !!k && all.indexOf(k) === i,
  );
  const prevByKey = new Map((prev.values ?? []).map((v) => [v.key, v] as const));
  const values = keys.map((key, slot) =>
    prevKeys[slot] === key
      ? detailToValue(key, next[`detail_${slot}`]) // same slot: take the edited details
      : (prevByKey.get(key) ?? { key }), // moved or newly added: keep what was known
  );
  const out: SourceConfig = { entity: next.entity };
  if (next.attribute) out.attribute = next.attribute;
  if (next.time_key) out.time_key = next.time_key;
  if (values.length) out.values = values;
  return out;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Schema = any[];

export function buildSourceSchema(
  form: FormData,
  info: SourceInfo,
  entityIds: string[] | undefined,
  t: Translate,
): Schema {
  const keys: string[] = [form.value_key, ...(form.extra_keys ?? [])].filter(Boolean);
  const select = (options: string[], multiple = false) => ({
    select: { options, multiple, mode: "dropdown" },
  });
  return [
    {
      name: "entity",
      required: true,
      selector: { entity: entityIds ? { include_entities: entityIds } : {} },
    },
    { name: "attribute", selector: select(withCurrent(info.listAttributes, form.attribute)) },
    { name: "time_key", selector: select(withCurrent(info.timeKeys, form.time_key)) },
    { name: "value_key", selector: select(withCurrent(info.numericKeys, form.value_key)) },
    {
      name: "extra_keys",
      selector: select(
        info.numericKeys.filter((k) => k !== form.value_key),
        true,
      ),
    },
    ...keys.map((key, i) => ({
      type: "expandable",
      name: `detail_${i}`,
      title: `${t("details")}: ${key}`,
      schema: [
        { name: "name", selector: { text: {} } },
        { name: "color", selector: { color_rgb: {} } },
        { name: "factor", selector: { number: { mode: "box", step: "any" } } },
        { name: "offset", selector: { number: { mode: "box", step: "any" } } },
        { name: "unit", selector: { text: {} } },
        {
          name: "shape",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "hv", label: t("shape_hv") },
                { value: "linear", label: t("shape_linear") },
              ],
            },
          },
        },
        {
          name: "axis",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "auto", label: t("axis_auto") },
                { value: "left", label: t("axis_left") },
                { value: "right", label: t("axis_right") },
              ],
            },
          },
        },
        { name: "visible", selector: { boolean: {} } },
      ],
    })),
  ];
}

export function buildGlobalSchema(t: Translate): Schema {
  return [
    { name: "title", selector: { text: {} } },
    { name: "height", selector: { number: { mode: "box", min: 100, max: 1500, step: 10 } } },
    {
      name: "time_range",
      selector: {
        select: {
          mode: "dropdown",
          options: [
            { value: "all", label: t("time_range_all") },
            { value: "from_now", label: t("time_range_from_now") },
          ],
        },
      },
    },
    { name: "show_now", selector: { boolean: {} } },
    { name: "show_legend", selector: { boolean: {} } },
  ];
}

/** Keeps a configured value selectable even if the current state no longer offers it. */
function withCurrent(options: string[], current: string | undefined): string[] {
  return current && !options.includes(current) ? [current, ...options] : options;
}
