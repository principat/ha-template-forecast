import { describe, expect, it } from "vitest";
import { normalizeConfig } from "../src/config";
import { buildFigure, toLocalString } from "../src/figure";
import type { States } from "../src/resolve";
import { buildSeries } from "../src/series";

const T0 = Date.UTC(2026, 9, 2, 15);
const hour = (i: number) => new Date(T0 + i * 3600_000).toISOString();

const states: States = {
  "sensor.price": {
    state: "0.1",
    attributes: {
      friendly_name: "Price",
      unit_of_measurement: "€/kWh",
      forecast: [
        { time: hour(0), value: 0.1, outdoor_temp: 10 },
        { time: hour(1), value: 0.2, outdoor_temp: 11 },
        { time: hour(2), value: "bad", outdoor_temp: 12 },
      ],
    },
  },
  "sensor.power": {
    state: "1",
    attributes: {
      unit_of_measurement: "kW",
      data: [
        { start_time: hour(2), price_per_kwh: 3 },
        { start_time: hour(0), price_per_kwh: 1 },
      ],
    },
  },
  "sensor.dead": { state: "unavailable", attributes: {} },
};

const cfg = (sources: unknown[], extra: Record<string, unknown> = {}) =>
  normalizeConfig({ type: "t", sources, ...extra });

describe("buildSeries", () => {
  it("auto-detects attribute, time and value", () => {
    const r = buildSeries(cfg([{ entity: "sensor.price" }]), states, T0);
    expect(r.errors).toEqual([]);
    expect(r.series).toHaveLength(1);
    const s = r.series[0];
    expect(s.name).toBe("Price");
    expect(s.unit).toBe("€/kWh");
    expect(s.y).toEqual([0.1, 0.2]); // non-numeric entry skipped
    expect(s.shape).toBe("hv");
  });

  it("sorts by time and reads other attribute layouts", () => {
    const r = buildSeries(cfg([{ entity: "sensor.power" }]), states, T0);
    expect(r.series[0].y).toEqual([1, 3]);
    expect(r.series[0].t).toEqual([T0, T0 + 2 * 3600_000]);
  });

  it("applies factor, offset, name, color per value and keeps extra fields separate", () => {
    const r = buildSeries(
      cfg([
        {
          entity: "sensor.price",
          values: [
            { key: "value", factor: 100, name: "ct/kWh", color: "#ff0000" },
            { key: "outdoor_temp", offset: -10, axis: "right", unit: "°C" },
          ],
        },
      ]),
      states,
      T0,
    );
    const [a, b] = r.series;
    expect(a.y).toEqual([10, 20]);
    expect(a.name).toBe("ct/kWh");
    expect(a.color).toBe("#ff0000");
    expect(b.y).toEqual([0, 1, 2]);
    expect(b.name).toBe("Price – outdoor_temp");
    expect(b.unit).toBe("°C");
    expect(b.axis).toBe("right");
    expect(a.color).not.toBe(b.color);
  });

  it("puts a second unit on the right axis automatically", () => {
    const r = buildSeries(cfg([{ entity: "sensor.price" }, { entity: "sensor.power" }]), states, T0);
    expect(r.series.map((s) => s.axis)).toEqual(["left", "right"]);
    const same = buildSeries(
      cfg([{ entity: "sensor.price" }, { entity: "sensor.price" }]),
      states,
      T0,
    );
    expect(same.series.map((s) => s.axis)).toEqual(["left", "left"]);
  });

  it("reports problems per entity and keeps the other series", () => {
    const r = buildSeries(
      cfg([{ entity: "sensor.missing" }, { entity: "sensor.dead" }, { entity: "sensor.price" }]),
      states,
      T0,
    );
    expect(r.errors.map((e) => [e.entity, e.code])).toEqual([
      ["sensor.missing", "entity_missing"],
      ["sensor.dead", "entity_unavailable"],
    ]);
    expect(r.series).toHaveLength(1);
  });

  it("reports a missing configured field", () => {
    const r = buildSeries(cfg([{ entity: "sensor.price", values: [{ key: "nope" }] }]), states, T0);
    expect(r.errors[0].code).toBe("no_data");
  });

  it("ignores sources without an entity (freshly added in the editor)", () => {
    const r = buildSeries(cfg([{ entity: "" }]), states, T0);
    expect(r).toEqual({ series: [], errors: [] });
  });

  it("from_now keeps the currently active entry and what follows", () => {
    const r = buildSeries(
      cfg([{ entity: "sensor.price" }], { time_range: "from_now" }),
      states,
      T0 + 1.5 * 3600_000,
    );
    expect(r.series[0].y).toEqual([0.2]);
  });
});

describe("buildFigure", () => {
  const theme = { text: "#111", grid: "#ccc" };

  it("formats times in the given time zone", () => {
    expect(toLocalString(Date.UTC(2026, 9, 2, 15, 4), "Europe/Berlin")).toBe("2026-10-02 17:04:00");
    expect(toLocalString(Date.UTC(2026, 9, 2, 15, 4), "UTC")).toBe("2026-10-02 15:04:00");
  });

  it("builds traces, axes and the now marker", () => {
    const config = cfg([{ entity: "sensor.price" }, { entity: "sensor.power" }]);
    const fig = buildFigure(buildSeries(config, states, T0), config, theme, "UTC", T0);
    expect(fig.data).toHaveLength(2);
    expect(fig.data[1].yaxis).toBe("y2");
    expect(fig.layout.yaxis2).toBeDefined();
    expect((fig.layout.shapes as unknown[]).length).toBe(1);
    expect(fig.data[0].hovertemplate).toContain("€/kWh");
  });

  it("omits the right axis, marker and legend when not needed", () => {
    const config = cfg([{ entity: "sensor.price" }], { show_now: false, show_legend: false });
    const fig = buildFigure(buildSeries(config, states, T0), config, theme, "UTC", T0);
    expect(fig.layout.yaxis2).toBeUndefined();
    expect(fig.layout.shapes).toBeUndefined();
    expect(fig.layout.showlegend).toBe(false);
  });

  it("marks hidden series as legend-only", () => {
    const config = cfg([{ entity: "sensor.price", values: [{ key: "value", visible: false }] }]);
    const fig = buildFigure(buildSeries(config, states, T0), config, theme, "UTC", T0);
    expect(fig.data[0].visible).toBe("legendonly");
  });
});
