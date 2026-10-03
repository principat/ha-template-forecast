import { describe, expect, it } from "vitest";
import { normalizeConfig } from "../src/config";

describe("normalizeConfig", () => {
  it("accepts a minimal config", () => {
    expect(
      normalizeConfig({ type: "custom:forecast-chart-card", sources: [{ entity: "sensor.a" }] }),
    ).toEqual({ type: "custom:forecast-chart-card", sources: [{ entity: "sensor.a" }] });
  });

  it("accepts an empty card (stub without entities)", () => {
    expect(normalizeConfig({ type: "x" }).sources).toEqual([]);
  });

  it("rejects non-list sources and non-objects", () => {
    expect(() => normalizeConfig({ sources: "sensor.a" })).toThrow();
    expect(() => normalizeConfig(null)).toThrow();
  });

  it("cleans up values and drops invalid fields", () => {
    const cfg = normalizeConfig({
      type: "t",
      height: -5,
      time_range: "bogus",
      sources: [
        {
          entity: "sensor.a",
          values: [
            "value",
            {
              key: "outdoor_temp",
              factor: "2",
              offset: 3,
              shape: "linear",
              axis: "right",
              visible: false,
            },
            { nokey: true },
          ],
        },
      ],
    });
    expect(cfg.height).toBeUndefined();
    expect(cfg.time_range).toBeUndefined();
    expect(cfg.sources[0].values).toEqual([
      { key: "value" },
      { key: "outdoor_temp", offset: 3, shape: "linear", axis: "right", visible: false },
    ]);
  });
});
