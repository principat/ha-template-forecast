# Example 1: Feed-in tariff during negative market prices

**Mode:** Transform (convert an existing price forecast)

[Deutsche Version](../de/01-einspeisung-negative-preise.md)

## Goal

If you sell your power directly or receive a market-price-based feed-in
tariff, you get **no money** for feeding in while the market price is
negative (sometimes you even have to pay). During those hours the
optimization should therefore not feed in, but charge batteries, supply
consumers or curtail generation.

For this, a sensor is created that derives a **feed-in price** from the
market price:

- With a negative market price, feeding in is worth **0 €/kWh**.
- Otherwise a fixed tariff applies, which is reduced proportionally when the
  market price is low. This encourages grid-friendly behavior of the
  batteries.

A finished forecast list is needed because HAEO requires the price for every
time step of the planning horizon, not just the current value.

## Where it acts in HAEO

As the **export price** at the **grid connection (Grid)**. This is where you
normally enter the price for feeding in, in €/kWh. Select this sensor there
instead of a fixed value or a plain market price sensor.

> The exact field names may differ slightly depending on the HAEO version.

## Helper settings

| Setting | Value |
|---|---|
| Mode | Transform |
| Source entity | `sensor.EPEX_PRICE` |
| Source attribute | `data` |
| Target attribute | `forecast` |
| Unit | `€/kWh` |
| Device class | `monetary` |
| State class | `measurement` |
| Update interval | 60 min (the source provides fixed timestamps itself) |

## External sensors and values used

| Placeholder | What it represents | Unit | Expected format |
|---|---|---|---|
| `sensor.EPEX_PRICE` | Day-ahead electricity market price, e.g. from the *EPEX Spot* integration | €/kWh | **State:** current price as a number. **Attribute `data`:** list of entries `{start_time, end_time, price_per_kwh}`, timestamps as ISO 8601 with time zone, e.g. `2026-10-01T00:15:00+02:00` |
| `input_number.FEED_IN_TARIFF` | Tariff you receive for exported energy (number helper, create it yourself) | €/kWh | Number, e.g. `0.0786` (box mode, step 0.001) |

The source attribute may have a different name or different keys (e.g.
Tibber, aWATTar, Nordpool). In that case `item.price_per_kwh` and
`item.start_time` must be adapted in the templates.

## Constants in the template

| Constant | Meaning |
|---|---|
| `0` (in market price `< 0`) | Threshold and result: below a price of 0 €/kWh feeding in is valued at 0. If you also don't want to feed in at small positive prices, raise the threshold. |
| `0.20` | Deduction factor (20 %): if the market price is below the tariff, 20 % of the difference ("gap") is subtracted from the tariff. The lower the market price, the less feeding in pays off. `0` = pure fixed tariff, `1` = the tariff follows the market price completely. |
| `4` (in `round(4)`) | Rounding to 4 decimal places. |
| `0` (in `float(0)`) | Fallback if a sensor is `unavailable`/`unknown`. 0 is used in the calculation then. |

## State template

```jinja
{% set price = states('sensor.EPEX_PRICE') | float(0) %}
{% set tariff = states('input_number.FEED_IN_TARIFF') | float(0) %}
{% set gap = [tariff - price, 0] | max %}
{% if price < 0 %}
  {{ 0 }}
{% else %}
  {{ (tariff - 0.20 * gap) | round(4) }}
{% endif %}
```

The state is the value for the current point in time, i.e. the same
calculation as in the attribute template, just with the current market price.

## Attribute template

Evaluated once per entry of the source list (`data`). `item` is the
respective entry.

```jinja
{% set price = item.price_per_kwh | float(0) %}
{% set tariff = states('input_number.FEED_IN_TARIFF') | float(0) %}
{% set gap = [tariff - price, 0] | max %}
{% if price < 0 %}
  {{ 0 }}
{% else %}
  {{ (tariff - 0.20 * gap) | round(4) }}
{% endif %}
```

The result per entry is `{time, value}`: `time` is taken from the source's `start_time`
automatically, `value` is the template's result. The other fields of the source
(`end_time`, `price_per_kwh`) are not copied, which keeps the attribute small.

## Typical adaptations

- Change the source: adapt `sensor.EPEX_PRICE`, the source attribute and the
  keys `price_per_kwh` / `start_time`.
- Include grid fees or taxes: in the attribute template, add or subtract a
  fixed amount from `price` before comparing.
