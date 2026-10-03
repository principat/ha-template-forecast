# Example 4: Limit wallbox charging power (depending on another consumer)

**Mode:** Transform (convert the forecast of another consumer)

[Deutsche Version](../de/04-wallbox-leistungsbegrenzung.md)

## Goal

The wallbox and another large consumer (an air conditioner in the example)
are on the **same phase** (L1), whose fuse rating is limited. The wallbox may
only draw as much current as is still free on the phase, otherwise the fuse
trips or load management intervenes harshly.

The sensor calculates the **maximum possible charging power** for each time
step:

```
free [A] = phase limit − reserve for remaining base load − current of the other consumer
```

- If less than the minimum charging current (6 A) is free, the power is set
  to **0** (charging is not possible then).
- Otherwise it is capped at the maximum charging current (16 A) and
  converted to power (kW).

Because the forecast of the other consumer is the source, the limit drops
exactly in the hours when it consumes a lot (e.g. air conditioner at midday
in the heat or heat pump at night in the cold).

## Where it acts in HAEO

As the **maximum charge power (Max. Charge Power, in kW)** in the battery
element that represents the EV. Select the sensor there instead of a fixed
value.

> The exact field names may differ slightly depending on the HAEO version.

## Helper settings

| Setting | Value |
|---|---|
| Mode | Transform |
| Source entity | `sensor.CONSUMER_FORECAST` |
| Source attribute | `forecast` |
| Target attribute | `forecast` |
| Unit | `kW` |
| Device class | `power` |
| State class | `measurement` |
| Update interval | 15 min |

## External sensors and values used

| Placeholder | What it represents | Unit | Expected format |
|---|---|---|---|
| `sensor.CONSUMER_FORECAST` | Power forecast of the other consumer on the same phase | kW | Attribute `forecast`: list of entries `{time, value}`, `value` in **kW** (e.g. `0.5591`) |
| `input_number.WALLBOX_PHASE_LIMIT` | Maximum current the phase may carry in total (fuse rating or grid connection; number helper, create it yourself) | A | Number, e.g. `25` |
| `input_number.WALLBOX_BASE_LOAD_RESERVE` | Current kept free for all other, unforecasted consumers on the phase (lighting, household appliances, …; number helper, create it yourself) | A | Number, e.g. `4` |

The number helpers make it possible to change limit and reserve on a
dashboard without editing the template.

## Constants in the template

| Constant | Meaning |
|---|---|
| `230` | Mains voltage in V (line to neutral), used to convert the power of the other consumer to amperes: `A = W / 230`. |
| `6` | Minimum charging current in A. Below this, wallbox and car cannot charge (AC charging standard). Below it the power is set to 0. |
| `16` | Maximum charging current per phase in A (limit of wallbox/car, here an 11 kW setup). |
| `0.69` | kW per ampere of charging current for **3-phase** charging: `3 × 230 V / 1000`. Use `0.23` for single-phase charging. |
| `25` (in `float(25)`) | Fallback for the phase limit if the helper is unavailable. |
| `4` (in `float(4)`) | Fallback for the reserve if the helper is unavailable. |
| `0` (in `float(0)`) | Fallback if the source value is missing. |
| `1000` | Conversion kW → W. |
| `2` (in `round(2)`) | Rounding to 2 decimal places. |

Note: because the wallbox applies the limit **symmetrically** to all phases,
the most heavily loaded phase (here L1) determines the charging power.

## State template

```jinja
{{ forecast[0].value }}
```

The state is the current value, i.e. the first entry of the calculated
forecast (`forecast` here is the already finished result list).

## Attribute template

Evaluated once per entry of the source list. `value` is `item.value`, i.e.
the power of the other consumer in kW.

```jinja
{% set a = states('input_number.WALLBOX_PHASE_LIMIT') | float(25)
         - states('input_number.WALLBOX_BASE_LOAD_RESERVE') | float(4)
         - value | float(0) * 1000 / 230 %}
{{ (0 if a < 6 else ([a, 16] | min) * 0.69) | round(2) }}
```

The result per entry is a number in kW. The timestamp (`time`) is taken from
the source list.

## Typical adaptations

- Single-phase charging: replace `0.69` with `0.23`.
- Different maximum wallbox current: adapt `16` (e.g. `32` for 22 kW).
- Several consumers on the phase: build a sum in the source (e.g. another
  forecast sensor) or add up the values in `value` in the template.
- If the source reports watts instead of kW: remove `* 1000`.
