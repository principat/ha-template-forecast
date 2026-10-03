# Examples

Practical examples for using Template Forecast together with
[HAEO](https://haeo.io) (Home Assistant Energy Optimizer). They come from a
running installation and can be adopted with small adaptations: replace
placeholders like `sensor.EPEX_PRICE` with your own entities, check the
constants, done.

[Deutsche Version](../de/README.md)

## Overview

| # | Use case | Mode | Acts in HAEO as |
|---|---|---|---|
| 1 | [Disable feed-in during negative market prices](01-feed-in-negative-prices.md) | Transform | Export price at the grid connection |
| 2 | [EV: availability (as a charging cost signal)](02-ev-availability.md) | Generate | Charge price of the EV battery |
| 3 | [EV: charging behavior (target state of charge by a time)](03-ev-target-soc.md) | Generate | Target/minimum SoC of the EV battery |
| 4 | [Limit wallbox charging power by another consumer](04-wallbox-power-limit.md) | Transform | Maximum charge power of the EV battery |
| 5 | [Solar charge lateness: charge the battery early in the day](05-solar-charge-lateness.md) | Generate | Additional cost for charging the home battery |

Examples 2 and 3 belong together and control EV charging jointly: 2 forecasts
the **availability** of the car, 3 the **charging behavior** (to what level
and by when it should be charged).

## Structure of the examples

Every file is structured the same way:

1. **Goal**: why the sensor was created
2. **Where it acts in HAEO**
3. **Helper settings**: mode, horizon, unit, etc.
4. **External sensors and values used**: what they represent, unit, expected
   format
5. **Constants in the template**: what fixed numbers mean (pure conversion
   factors like 1000 or 60 excluded)
6. **State template** with placeholders
7. **Attribute template** with placeholders

## How to adopt an example

1. Create the required number/switch helpers
   (Settings → Devices & services → Helpers), if the example mentions them.
2. Settings → Devices & services → Helpers → "Create helper" →
   **Template Forecast**, choose the mode given in the example.
3. Replace the placeholders in both templates with your entities and adapt
   the constants to your installation.
4. Set unit, device class and state class as in the example.
5. Select the created sensor in HAEO at the stated place.
6. Check the sensor in the developer tools: the state must be plausible and
   the `forecast` attribute a list of `time` and `value`.

## Notes

- **Horizon:** number of steps × step size should match the HAEO horizon (72
  × 60 min in the examples).
- **Time zone:** `now()` returns local time. The time-of-day logic of
  examples 2 and 3 therefore refers to your local time.
- **Fallbacks:** `| float(0)`, `| bool(false)` and similar prevent errors when
  a sensor is briefly `unavailable`. They should be kept.

## Share your own example

You have a useful configuration? Open an issue with the
["Example" template](https://github.com/principat/ha-template-forecast/issues/new?template=example.yml).
