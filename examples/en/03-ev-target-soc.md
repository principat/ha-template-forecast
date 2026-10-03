# Example 3: EV target state of charge at a given time (deadline)

**Mode:** Generate (create a forecast from a schedule and settings)

[Deutsche Version](../de/03-ev-ziel-ladezustand.md)

This example belongs together with
[Example 2: Availability](02-ev-availability.md): that one forecasts **when
the car is available**, this one the **charging behavior**: to what level and
by when it should be charged.

## Goal

The car should be charged to a desired state of charge by a certain time (e.g.
6 am, when you leave). At all other times a low base value is enough.

For this, the sensor provides a target state of charge in percent for every
hour of the horizon:

- at the configured target hour: the desired target state of charge,
- otherwise: a base value (baseline).

Target hour and target state of charge can be changed, e.g. on a dashboard,
via two number helpers without touching the template.

> **Warning: the target value is not a guarantee.**
> HAEO does not treat the target state of charge as a hard limit. Falling
> below the value only causes **costs** in the optimization, which are weighed
> against all other costs and revenues (electricity prices, feed-in, wear,
> etc.). HAEO therefore still decides on its own whether the car is really
> charged to the target value. If falling below it is cheaper in a given
> situation, it is accepted.
>
> If you rely on the car being charged enough at the target time (e.g. for
> the drive to work), you should **add an additional safeguard in the wallbox
> control**. For example, an automation that charges at full power
> independently of HAEO if the state of charge is still too low shortly
> before the target hour.

## Where it acts in HAEO

As a **time-dependent target/minimum state of charge (SoC, in %)** in the
battery element that represents the EV. Select the sensor there instead of a
fixed value. HAEO then plans charging so that the value is reached at the
respective hour.

> The exact field names may differ slightly depending on the HAEO version.

## Helper settings

| Setting | Value |
|---|---|
| Mode | Generate |
| Planning horizon | 72 steps of 60 minutes (must match the HAEO horizon) |
| Target attribute | `forecast` |
| Unit | `%` |
| Device class | empty |
| State class | `measurement` |
| Update interval | 60 min |

> The template works with **hourly steps** aligned to the full hour. With a
> different step size `timedelta(hours=index)` must be adapted.

## External sensors and values used

| Placeholder | What it represents | Unit | Expected format |
|---|---|---|---|
| `input_number.EV_TARGET_HOUR` | Time of day by which the car should be charged (number helper, create it yourself) | hour | Integer 0–23, local time, e.g. `6` |
| `input_number.EV_TARGET_SOC` | Desired state of charge at that hour (number helper, create it yourself) | % | Number 0–100, e.g. `60` (step 5) |

The current time is also used (`now()`, Home Assistant's local time zone).

## Constants in the template

| Constant | Meaning |
|---|---|
| `baseline = 40` | Base value in % that applies at all hours except the target hour. This is the state of charge that should always be kept as a lower bound (range reserve). `0` = no reserve. |
| `6` (in `int(6)`) | Fallback for the target hour if the number helper is unavailable. |
| `80` (in `float(80)`) | Fallback for the target state of charge if the number helper is unavailable. |
| `minute=0, second=0, microsecond=0` | Rounds "now" down to the full hour so the timestamps match the hourly values. |

## State template

```jinja
{% set target_hour = states('input_number.EV_TARGET_HOUR') | int(6) %}
{% set target_soc = states('input_number.EV_TARGET_SOC') | float(80) %}
{% set baseline = 40 %}
{{ target_soc if now().hour == target_hour else baseline }}
```

The state shows the currently valid value (target or base value).

## Attribute template

Evaluated once for every planning step. `index` is the step.

```jinja
{% set base = now().replace(minute=0, second=0, microsecond=0) %}
{% set target = base + timedelta(hours=index) %}
{% set target_hour = states('input_number.EV_TARGET_HOUR') | int(6) %}
{% set target_soc = states('input_number.EV_TARGET_SOC') | float(80) %}
{% set baseline = 40 %}
{{ {
   "time": target.isoformat(),
   "value": target_soc if target.hour == target_hour else baseline
   } }}
```

The template returns a dict with `time` and `value`. The timestamp is set
explicitly here because it is aligned to the local hour (the target hour
refers to local time, not UTC).

## Typical adaptations

- Multiple deadlines (e.g. weekdays differ from weekends): additionally check
  `target.weekday()` in the attribute template (0 = Monday … 6 = Sunday).
- Target only if the car is plugged in: additionally query
  `states('binary_sensor.EV_PLUGGED_IN') | bool(false)` and return `0`
  otherwise (see [Example 2](02-ev-availability.md)).
