# Example 2: EV availability (as a charging cost signal)

**Mode:** Generate (create a forecast from a schedule and a state)

[Deutsche Version](../de/02-ev-ladekosten.md)

This example belongs together with
[Example 3: Target state of charge](03-ev-target-soc.md): this one forecasts
the **availability** of the car (when is it ready to be charged?), example 3
the **charging behavior** (to what level and by when should it be charged?).

## Goal

HAEO needs to know in which hours the EV is available for charging at all:
only when it is plugged in and the time fits. Availability is expressed as a
price signal per hour:

- **Negative value** (bonus): charging is rewarded, the optimization
  preferably charges the car in these hours.
- **High positive value**: charging is "expensive", the optimization avoids
  it.

If the car is not plugged in, the value is always high. This way energy is
never planned for a car that is not charging.

The **time window** in the template mainly represents **known, regular
absences** (e.g. working hours). The "plugged in" sensor only knows the
current state. Without the window HAEO would still plan charging for the hours
in which the car is usually not at home, just because the car is plugged in
right now.

The value is not a real electricity price but a **control instrument**: it
shifts the charging decision into the desired hours.

## Where it acts in HAEO

As the **price for charging the EV battery**, in the battery element that
represents the car (charge/discharge costs, in €/kWh). Select the sensor there
instead of a fixed value.

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

> The template works with **hourly steps**. With a different step size the
> hour calculation must be adapted.

## External sensors and values used

| Placeholder | What it represents | Unit | Expected format |
|---|---|---|---|
| `binary_sensor.EV_PLUGGED_IN` | Is the charging cable plugged into the car / wallbox? | – | `on` / `off`. `unavailable`/`unknown` is treated as "not plugged in" (`bool(false)`) |

The current time is also used (`now()`, in Home Assistant's local time
zone). `index` is the step index (0 = now, 1 = in one hour, …).

## Constants in the template

| Constant | Meaning |
|---|---|
| `-0.06` | Bonus in €/kWh when charging is desired (car plugged in and time within the charging window). The more negative, the stronger the charging. |
| `0.26` | "Blocking price" in €/kWh: charging is undesired (car not plugged in or inside the absence window). Ideally around the grid purchase price or above, so HAEO does not recharge from the grid. Here `0.26` is below the actual grid purchase cost, which means it also works with dynamic grid fees. |
| `7` and `12` | Hour limits (local time) during which the car is **expected to be unavailable**, e.g. because of working hours. Here: hours 7 up to and including 12 are blocked, charging is desired before 7 am (night) and from 1 pm. Adapt to your own regular absences. Side effect: during that time the optimization fills other batteries more strongly so the car can be charged from them afterwards. |
| `24` | Hours per day, so the hour index wraps around to 0 after midnight. |
| `false` (in `bool(false)`) | Fallback for an unavailable sensor. |

## State template

```jinja
{% if states('binary_sensor.EV_PLUGGED_IN') | bool(false) %}
  -0.06
{% else %}
  0.26
{% endif %}
```

The state shows the currently valid value, here without the time window
check. It is for display only. HAEO reads the values from the attribute.

## Attribute template

Evaluated once for every planning step. `index` is the step.

```jinja
{% set hourOfDay = (now().hour + index) % 24 %}
{% if states('binary_sensor.EV_PLUGGED_IN') | bool(false) and ((hourOfDay < 7) or (hourOfDay > 12)) %}
  -0.06
{% else %}
  0.26
{% endif %}
```

The result per step is a single number. The timestamp (`time`) is added
automatically.

## Typical adaptations

- Change the absence window: replace `7` and `12`, e.g. with your own working
  hours. For a window that spans midnight, or to allow only a charging window
  (e.g. only at night 22–6), invert the condition:
  `hourOfDay >= 22 or hourOfDay < 6`.
- Different times on weekdays and weekends: additionally check
  `(now() + timedelta(hours=index)).weekday() < 5`.
- No time window wanted: remove the part after `and`. The car is then charged
  whenever it is plugged in, at the cheapest times according to the
  optimization.
