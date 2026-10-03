import { describe, expect, it } from "vitest";
import {
  entryKeys,
  listAttributes,
  numericKeys,
  parseTime,
  pickListAttribute,
  pickTimeKey,
  pickValueKey,
  timeKeys,
  toNumber,
} from "../src/detect";

const forecast = [
  { time: "2026-10-02T15:00:00+00:00", value: 0.5, outdoor_temp: 15.9, label: "a" },
  { time: "2026-10-02T16:00:00+00:00", value: 0.6, outdoor_temp: 15.7, label: "b" },
];
const epex = [
  {
    start_time: "2026-10-01T00:00:00+02:00",
    end_time: "2026-10-01T00:15:00+02:00",
    price_per_kwh: 0.16,
  },
];

describe("listAttributes / pickListAttribute", () => {
  const attrs = { friendly_name: "x", forecast, data: epex, empty: [], numbers: [1, 2, 3] };

  it("finds attributes holding lists of objects only", () => {
    expect(listAttributes(attrs)).toEqual(["forecast", "data"]);
    expect(listAttributes(undefined)).toEqual([]);
  });

  it("prefers forecast, then the hint, then data, then the first", () => {
    expect(pickListAttribute(["data", "forecast"])).toBe("forecast");
    expect(pickListAttribute(["data", "plan"], "plan")).toBe("plan");
    expect(pickListAttribute(["other", "data"])).toBe("data");
    expect(pickListAttribute(["other", "more"])).toBe("other");
    expect(pickListAttribute([])).toBeUndefined();
  });
});

describe("time detection", () => {
  it("parses ISO strings, Dates and unix timestamps", () => {
    expect(parseTime("2026-10-02T15:00:00+00:00")).toBe(Date.UTC(2026, 9, 2, 15));
    expect(parseTime(new Date(1000))).toBe(1000);
    expect(parseTime(1_700_000_000)).toBe(1_700_000_000_000);
    expect(parseTime(1_700_000_000_000)).toBe(1_700_000_000_000);
    expect(parseTime("hello")).toBeNull();
    expect(parseTime(null)).toBeNull();
  });

  it("detects time keys and does not mistake values for timestamps", () => {
    expect(timeKeys(forecast)).toEqual(["time"]);
    expect(timeKeys(epex)).toEqual(["start_time", "end_time"]);
    expect(timeKeys([{ value: 1_700_000_000, time: 1_700_000_000 }])).toEqual(["time"]);
  });

  it("picks the best time key", () => {
    expect(pickTimeKey(["end_time", "start_time"])).toBe("start_time");
    expect(pickTimeKey(["time", "start_time"])).toBe("time");
    expect(pickTimeKey(["foo"])).toBe("foo");
    expect(pickTimeKey([])).toBeUndefined();
  });
});

describe("value detection", () => {
  it("finds numeric keys, excluding the time key and text", () => {
    expect(numericKeys(forecast, ["time"])).toEqual(["value", "outdoor_temp"]);
    expect(numericKeys(epex, ["start_time"])).toEqual(["price_per_kwh"]);
  });

  it("accepts numeric strings", () => {
    expect(toNumber("1.5")).toBe(1.5);
    expect(toNumber("-2e3")).toBe(-2000);
    expect(toNumber("abc")).toBeNull();
    expect(toNumber(NaN)).toBeNull();
    expect(numericKeys([{ time: "2026-10-02T15:00:00Z", v: "0.5" }], ["time"])).toEqual(["v"]);
  });

  it("prefers 'value'", () => {
    expect(pickValueKey(["outdoor_temp", "value"])).toBe("value");
    expect(pickValueKey(["price_per_kwh"])).toBe("price_per_kwh");
    expect(pickValueKey([])).toBeUndefined();
  });

  it("collects entry keys in order of appearance", () => {
    expect(entryKeys([{ a: 1 }, { b: 2, a: 3 }])).toEqual(["a", "b"]);
    expect(entryKeys("nope")).toEqual([]);
  });
});
