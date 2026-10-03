import { describe, expect, it } from "vitest";
import type { SourceConfig } from "../src/config";
import { translator } from "../src/i18n";
import { describeSource, type States } from "../src/resolve";
import { applyForm, buildSourceSchema, hexToRgb, rgbToHex, sourceToForm } from "../src/schema";

const states: States = {
  "sensor.a": {
    state: "1",
    attributes: {
      forecast: [{ time: "2026-10-02T15:00:00Z", value: 1, temp: 2 }],
      data: [{ start_time: "2026-10-02T15:00:00Z", price: 3 }],
    },
  },
  "sensor.b": {
    state: "1",
    attributes: { forecast: [{ time: "2026-10-02T15:00:00Z", value: 7 }] },
  },
};
const infoFor = (cfg: SourceConfig) => describeSource(cfg, states[cfg.entity]);
const t = translator("en");

describe("describeSource", () => {
  it("returns the detected selection and the choices", () => {
    const info = infoFor({ entity: "sensor.a" });
    expect(info.listAttributes).toEqual(["forecast", "data"]);
    expect(info.attribute).toBe("forecast");
    expect(info.timeKey).toBe("time");
    expect(info.numericKeys).toEqual(["value", "temp"]);
    expect(info.valueKey).toBe("value");
  });

  it("keeps a configured attribute", () => {
    const info = infoFor({ entity: "sensor.a", attribute: "data" });
    expect(info.timeKey).toBe("start_time");
    expect(info.valueKey).toBe("price");
  });

  it("copes with unknown entities", () => {
    expect(infoFor({ entity: "sensor.nope" }).listAttributes).toEqual([]);
  });
});

describe("editor <-> config mapping", () => {
  it("fills auto-detected values into the form", () => {
    const form = sourceToForm({ entity: "sensor.a" }, infoFor({ entity: "sensor.a" }));
    expect(form).toMatchObject({
      entity: "sensor.a",
      attribute: "forecast",
      time_key: "time",
      value_key: "value",
      extra_keys: [],
    });
    expect(form.detail_0).toMatchObject({
      factor: 1,
      offset: 0,
      shape: "hv",
      axis: "auto",
      visible: true,
    });
  });

  it("re-detects everything when the entity changes", () => {
    const prev: SourceConfig = {
      entity: "sensor.a",
      attribute: "data",
      time_key: "start_time",
      values: [{ key: "price", factor: 5 }],
    };
    const prevForm = sourceToForm(prev, infoFor(prev));
    const next = applyForm(prev, prevForm, { ...prevForm, entity: "sensor.b" }, infoFor);
    expect(next).toEqual({
      entity: "sensor.b",
      attribute: "forecast",
      time_key: "time",
      values: [{ key: "value" }],
    });
  });

  it("re-detects time and value when the attribute changes", () => {
    const prev: SourceConfig = { entity: "sensor.a" };
    const prevForm = sourceToForm(prev, infoFor(prev));
    const next = applyForm(prev, prevForm, { ...prevForm, attribute: "data" }, infoFor);
    expect(next).toEqual({
      entity: "sensor.a",
      attribute: "data",
      time_key: "start_time",
      values: [{ key: "price" }],
    });
  });

  it("stores details only where they differ from the defaults", () => {
    const prev: SourceConfig = { entity: "sensor.a" };
    const prevForm = sourceToForm(prev, infoFor(prev));
    const next = applyForm(
      prev,
      prevForm,
      {
        ...prevForm,
        detail_0: {
          ...prevForm.detail_0,
          name: "Preis",
          color: [255, 0, 0],
          factor: 100,
          shape: "linear",
        },
      },
      infoFor,
    );
    expect(next.values).toEqual([
      { key: "value", name: "Preis", color: "#ff0000", factor: 100, shape: "linear" },
    ]);
  });

  it("adds extra value fields with defaults and keeps existing details", () => {
    const prev: SourceConfig = { entity: "sensor.a", values: [{ key: "value", factor: 2 }] };
    const prevForm = sourceToForm(prev, infoFor(prev));
    const next = applyForm(prev, prevForm, { ...prevForm, extra_keys: ["temp"] }, infoFor);
    expect(next.values).toEqual([{ key: "value", factor: 2 }, { key: "temp" }]);
  });

  it("swapping the primary and an extra field keeps each field's own settings", () => {
    const prev: SourceConfig = {
      entity: "sensor.a",
      values: [{ key: "value" }, { key: "temp", offset: 1 }],
    };
    const prevForm = sourceToForm(prev, infoFor(prev));
    const next = applyForm(
      prev,
      prevForm,
      { ...prevForm, value_key: "temp", extra_keys: ["value"] },
      infoFor,
    );
    expect(next.values).toEqual([{ key: "temp", offset: 1 }, { key: "value" }]);
  });

  it("converts colors both ways", () => {
    expect(hexToRgb("#ff8000")).toEqual([255, 128, 0]);
    expect(hexToRgb("nope")).toBeUndefined();
    expect(rgbToHex([255, 128, 0])).toBe("#ff8000");
    expect(rgbToHex(undefined)).toBeUndefined();
  });
});

describe("buildSourceSchema", () => {
  it("offers one details section per plotted field and the detected choices", () => {
    const src: SourceConfig = { entity: "sensor.a", values: [{ key: "value" }, { key: "temp" }] };
    const info = infoFor(src);
    const schema = buildSourceSchema(sourceToForm(src, info), info, ["sensor.a"], t);
    expect(schema.filter((s) => s.type === "expandable").map((s) => s.name)).toEqual([
      "detail_0",
      "detail_1",
    ]);
    expect(schema.find((s) => s.name === "attribute").selector.select.options).toEqual([
      "forecast",
      "data",
    ]);
    expect(schema.find((s) => s.name === "extra_keys").selector.select.options).toEqual(["temp"]);
    expect(schema[0].selector.entity.include_entities).toEqual(["sensor.a"]);
  });
});
