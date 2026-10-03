# Example 5: Solar charge lateness (charge early, don't dawdle)

**Mode:** Generate (create a forecast from several PV forecasts)

[Deutsche Version](../de/05-solar-ladeverzoegerung.md)

## Goal

The battery should be **charged from the sun as early in the day as
possible**, not only in the late afternoon. Without an additional signal it
makes no difference to the optimization whether it puts the solar energy into
the battery at 10 am or at 3 pm. If clouds suddenly appear in the afternoon,
the battery is then often not full.

For this, the sensor produces a **cost curve that rises hourly from the
moment the PV system starts producing**: charging shortly after PV start is
slightly rewarded (negative), the later, the more "expensive", up to an upper
limit. The optimization therefore preferably charges at the beginning of the
sun window.

As with the EV examples, the value is **not a real price** but a control
instrument with small amounts. It should only decide when everything else
would be equal.

## Where it acts in HAEO

As an **additional price/cost term for charging the home battery** (in
€/kWh), in the battery element or in a policy that rates charging. Select the
sensor there instead of a fixed value.

> The exact field names may differ slightly depending on the HAEO version.

## Helper settings

| Setting | Value |
|---|---|
| Mode | Generate |
| Planning horizon | 72 steps of 60 minutes (must match the HAEO horizon) |
| Target attribute | `forecast` |
| Unit | `€/kWh` |
| Device class | `monetary` |
| State class | `measurement` |
| Update interval | 60 min |

> The template works with **hourly steps** (`timedelta(hours=index)`). With a
> different step size this must be adapted.

## External sensors and values used

| Placeholder | What it represents | Unit | Expected format |
|---|---|---|---|
| `sensor.PV_SYSTEM_1`, `sensor.PV_SYSTEM_2`, … | **HAEO output sensors** per solar element ("Power" entity of the respective solar element, e.g. `sensor.solar_roof_south_power`). Any number, enter them in the `solar_sensors` list | kW | Attribute `forecast`: list of entries `{time, value}`, `value` in **kW**, e.g. `0.096` |

So these are not the input forecasts (e.g. from Forecast.Solar) but the
**optimized PV power calculated by HAEO** for each system. Two consequences:

- The sensor depends on the result of the last optimization and feeds back
  into the next one via battery charging. This is intended here and
  uncritical because the amounts are small.
- If PV is curtailed (e.g. at negative prices), the optimized power drops and
  may fall below the threshold. The "PV start" can then shift. If that
  bothers you, use the forecast sensors that also serve as input for the solar
  elements in HAEO instead.

Important: all sensors must have the **same time grid and the same length**
in `forecast`. The template adds up the entries at the same position and uses
the timestamps of the first system. HAEO output sensors fulfill this because
they are based on the same optimization horizon.

## Constants in the template

| Constant | Meaning |
|---|---|
| `threshold = 0.1` | Threshold in kW for the **summed** PV power. Only above it counts as "PV running"; below it is night/twilight. Prevents minimal twilight output from counting as sunrise. |
| `base = -0.005` | Start value in €/kWh right at PV start (a slight bonus for charging) and value at night when no PV start is found in the forecast. |
| `rate = 0.003` | Increase in €/kWh **per hour** since PV start. The higher, the more early charging is preferred. |
| `max_ramp = 0.02` | Upper limit of the increase in €/kWh. The value thus rises to at most `base + max_ramp` (here `0.015`). This keeps the influence small compared to real prices. |
| `3600` | Seconds per hour, conversion only. |
| `4` (in `round(4)`) | Rounding to 4 decimal places. |

## State template

```jinja
{% set solar_sensors = [
    'sensor.PV_SYSTEM_1', 'sensor.PV_SYSTEM_2', 'sensor.PV_SYSTEM_3'
  ] %}
{% set threshold = 0.1 %}
{% set base = -0.005 %}
{% set rate = 0.003 %}
{% set max_ramp = 0.02 %}
{% set forecasts = solar_sensors | map('state_attr', 'forecast') | list %}
{% set ns = namespace(pv_starts=[], was_dark=true) %}
{% for i in range(forecasts[0] | length) %}
  {% set total = forecasts | map(attribute=i) | map(attribute='value') | sum %}
  {% if ns.was_dark and total > threshold %}
    {% set ns.pv_starts = ns.pv_starts + [forecasts[0][i].time] %}
  {% endif %}
  {% set ns.was_dark = total <= threshold %}
{% endfor %}
{% set target = now() %}
{% set past = ns.pv_starts | select('le', target) | list %}
{% if past | length == 0 %}
  {{ base }}
{% else %}
  {% set last_start = past[-1] %}
  {% set hours_since = ((target - last_start).total_seconds() / 3600) %}
  {{ (base + ([hours_since * rate, max_ramp] | min)) | round(4) }}
{% endif %}
```

The state is the same curve, evaluated for "now" (`target = now()`).

## Attribute template

Evaluated once for every planning step. `index` is the step. It differs from
the state template only in the target time.

```jinja
{% set solar_sensors = [
    'sensor.PV_SYSTEM_1', 'sensor.PV_SYSTEM_2', 'sensor.PV_SYSTEM_3'
  ] %}
{% set threshold = 0.1 %}
{% set base = -0.005 %}
{% set rate = 0.003 %}
{% set max_ramp = 0.02 %}
{% set forecasts = solar_sensors | map('state_attr', 'forecast') | list %}
{% set ns = namespace(pv_starts=[], was_dark=true) %}
{% for i in range(forecasts[0] | length) %}
  {% set total = forecasts | map(attribute=i) | map(attribute='value') | sum %}
  {% if ns.was_dark and total > threshold %}
    {% set ns.pv_starts = ns.pv_starts + [forecasts[0][i].time] %}
  {% endif %}
  {% set ns.was_dark = total <= threshold %}
{% endfor %}
{% set target = now() + timedelta(hours=index) %}
{% set past = ns.pv_starts | select('le', target) | list %}
{% if past | length == 0 %}
  {{ base }}
{% else %}
  {% set last_start = past[-1] %}
  {% set hours_since = ((target - last_start).total_seconds() / 3600) %}
  {{ (base + ([hours_since * rate, max_ramp] | min)) | round(4) }}
{% endif %}
```

How it works: first, the **PV starts** are determined from the sum of all PV
forecasts (transition from "below threshold" to "above threshold"). Then, for
the target time, the last PV start before it is looked up and the time since
then is converted into the increase.

## Typical adaptations

- More PV systems: just add them to `solar_sensors` (in both templates).
- Stronger or weaker push towards early charging: adapt `rate` and
  `max_ramp`.
- If the sensor is evaluated for the first time in the middle of the day, the
  forecast already starts inside the "sun window". The first entry then counts
  as the PV start, so the increase starts from "now" rather than from the real
  sunrise. For the optimization this is uncritical in practice.
