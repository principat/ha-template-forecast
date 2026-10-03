"""The Forecast Chart dashboard card inside a real Home Assistant frontend.

The unit tests in frontend/test cover the logic; this checks what only a real instance can:
the integration registers and serves the bundle, the card draws a Plotly chart from real
entity states, and the card editor (built on HA's own `ha-form`) opens an existing
configuration without overwriting it and reports changes the way Lovelace expects.
"""
from __future__ import annotations

import pytest

CARD = "forecast-chart-card"
EDITOR = "forecast-chart-card-editor"

SET_UP_ENTITIES = """
async () => {
  const ha = document.querySelector('home-assistant');
  const base = Date.now() - (Date.now() % 3600000);
  const iso = (i) => new Date(base + i * 3600000).toISOString();
  await ha.hass.callApi('POST', 'states/sensor.e2e_forecast', {
    state: '0.1',
    attributes: {
      friendly_name: 'E2E Forecast',
      unit_of_measurement: '€/kWh',
      forecast: Array.from({length: 24}, (_, i) => ({
        time: iso(i), value: i % 2 ? 0.2 : 0.1, outdoor_temp: 10 + i / 4,
      })),
    },
  });
  await ha.hass.callApi('POST', 'states/sensor.e2e_prices', {
    state: '0.3',
    attributes: {
      friendly_name: 'E2E Prices',
      unit_of_measurement: '€/kWh',
      data: Array.from({length: 24}, (_, i) => ({
        start_time: iso(i), end_time: iso(i + 1), price_per_kwh: 0.3 + i / 100,
      })),
    },
  });
}
"""


ENSURE_HELPER = """
async () => {
  // The integration (and with it the card) is only loaded once a helper exists.
  const ha = document.querySelector('home-assistant');
  const entries = await ha.hass.callApi('GET', 'config/config_entries/entry');
  if (entries.some((e) => e.domain === 'template_forecast')) return false;
  const flow = await ha.hass.callApi('POST', 'config/config_entries/flow', {
    handler: 'template_forecast',
  });
  const next = await ha.hass.callApi('POST', `config/config_entries/flow/${flow.flow_id}`, {
    name: 'E2E helper',
    mode: 'generate',
  });
  const done = await ha.hass.callApi('POST', `config/config_entries/flow/${next.flow_id}`, {
    attribute_template: '{{ index }}',
  });
  if (done.type !== 'create_entry') throw new Error(JSON.stringify(done));
  return true;
}
"""


@pytest.fixture
def ha_page(page):
    page.goto("/", wait_until="networkidle")
    page.wait_for_function("() => !!document.querySelector('home-assistant')?.hass?.states")
    if page.evaluate(ENSURE_HELPER):
        # the card is added to the frontend on page load, so load the page again
        page.goto("/", wait_until="networkidle")
        page.wait_for_function("() => !!document.querySelector('home-assistant')?.hass?.states")
    page.evaluate(SET_UP_ENTITIES)
    page.wait_for_function(
        "() => !!document.querySelector('home-assistant').hass.states['sensor.e2e_prices']"
    )
    return page


def test_bundle_is_served_and_card_is_registered(ha_page):
    response = ha_page.request.get("/forecast-chart-card/forecast-chart-card.js")
    assert response.ok, response.status
    assert "forecast-chart-card" in response.text()

    ha_page.wait_for_function(f"() => !!customElements.get('{CARD}')", timeout=10000)
    registered = ha_page.evaluate(
        f"() => (window.customCards || []).some((c) => c.type === '{CARD}')"
    )
    assert registered


def test_card_draws_one_trace_per_value_field(ha_page):
    traces = ha_page.evaluate(
        f"""
        async () => {{
          const ha = document.querySelector('home-assistant');
          const card = document.createElement('{CARD}');
          card.setConfig({{
            type: 'custom:{CARD}',
            sources: [{{entity: 'sensor.e2e_forecast', values: [{{key: 'value'}}, {{key: 'outdoor_temp'}}]}}],
          }});
          card.hass = ha.hass;
          card.style.cssText = 'position:fixed;top:0;left:0;width:800px;z-index:99999;background:#fff';
          document.body.appendChild(card);
          for (let i = 0; i < 50 && !card.querySelector('.scatterlayer .trace'); i++) {{
            await new Promise((r) => setTimeout(r, 100));
          }}
          return card.querySelectorAll('.scatterlayer .trace').length;
        }}
        """
    )
    assert traces == 2


def test_card_inside_a_shadow_root_keeps_legend_and_axis_titles_in_the_card(ha_page):
    """Home Assistant puts cards into shadow roots, where Plotly's global stylesheet does not
    apply. Without the card copying it, the second SVG layer (axis titles, legend) is not
    stacked on the first and ends up below the chart, outside the card."""
    result = ha_page.evaluate(
        f"""
        async () => {{
          const ha = document.querySelector('home-assistant');
          const host = document.createElement('div');
          host.style.cssText = 'position:fixed;top:0;left:0;width:360px;z-index:99999;background:#fff';
          document.body.appendChild(host);
          const root = host.attachShadow({{mode: 'open'}});
          const card = document.createElement('{CARD}');
          card.setConfig({{type: 'custom:{CARD}', sources: [{{entity: 'sensor.e2e_forecast'}}]}});
          card.hass = ha.hass;
          root.appendChild(card);
          for (let i = 0; i < 50 && !card.querySelector('.legend'); i++) {{
            await new Promise((r) => setTimeout(r, 100));
          }}
          // wait until the layout has settled (the legend moves while Plotly sizes the chart)
          const bottom = () => card.querySelector('.legend').getBoundingClientRect().bottom;
          for (let i = 0; i < 30; i++) {{
            const before = bottom();
            await new Promise((r) => setTimeout(r, 200));
            if (bottom() === before) break;
          }}
          const plot = card.querySelector('.tfc-plot').getBoundingClientRect();
          const legend = card.querySelector('.legend').getBoundingClientRect();
          const title = card.querySelector('.ytitle').getBoundingClientRect();
          return {{
            plotBottom: plot.bottom, legendBottom: legend.bottom,
            titleBottom: title.bottom, plotTop: plot.top, titleTop: title.top,
          }};
        }}
        """
    )
    assert result["legendBottom"] <= result["plotBottom"] + 1, result
    assert result["plotTop"] <= result["titleTop"] and result["titleBottom"] <= result["plotBottom"] + 1, result


def test_card_reports_a_missing_entity_without_breaking(ha_page):
    texts = ha_page.evaluate(
        f"""
        async () => {{
          const ha = document.querySelector('home-assistant');
          const card = document.createElement('{CARD}');
          card.setConfig({{type: 'custom:{CARD}', sources: [{{entity: 'sensor.e2e_forecast'}}, {{entity: 'sensor.nope'}}]}});
          card.hass = ha.hass;
          document.body.appendChild(card);
          for (let i = 0; i < 50 && !card.querySelector('.tfc-error'); i++) {{
            await new Promise((r) => setTimeout(r, 100));
          }}
          return {{
            errors: [...card.querySelectorAll('.tfc-error')].map((e) => e.textContent.trim()),
            traces: card.querySelectorAll('.scatterlayer .trace').length,
          }};
        }}
        """
    )
    assert len(texts["errors"]) == 1 and "sensor.nope" in texts["errors"][0]
    assert texts["traces"] == 1


def test_editor_opens_existing_config_and_reports_changes(ha_page):
    """An already configured card must come back as configured, and edits must be emitted."""
    result = ha_page.evaluate(
        f"""
        async () => {{
          const ha = document.querySelector('home-assistant');
          const editor = document.createElement('{EDITOR}');
          const changes = [];
          editor.addEventListener('config-changed', (e) => changes.push(e.detail.config));
          editor.setConfig({{
            type: 'custom:{CARD}',
            title: 'Stored title',
            sources: [{{
              entity: 'sensor.e2e_forecast',
              attribute: 'forecast',
              time_key: 'time',
              values: [{{key: 'value', factor: 100, name: 'Preis'}}, {{key: 'outdoor_temp'}}],
            }}],
          }});
          editor.hass = ha.hass;
          document.body.appendChild(editor);

          const wait = async (fn) => {{
            for (let i = 0; i < 80; i++) {{
              const v = fn();
              if (v) return v;
              await new Promise((r) => setTimeout(r, 100));
            }}
            return null;
          }};
          const forms = await wait(() => {{
            const f = editor.shadowRoot?.querySelectorAll('ha-form');
            return f && f.length >= 2 ? [...f] : null;
          }});
          if (!forms) return {{error: 'ha-form never rendered', defined: !!customElements.get('ha-form')}};
          const [globalForm, sourceForm] = forms;
          const shown = JSON.parse(JSON.stringify(sourceForm.data));

          // user raises the scaling factor of the first field
          sourceForm.dispatchEvent(new CustomEvent('value-changed', {{
            detail: {{value: {{...sourceForm.data, detail_0: {{...sourceForm.data.detail_0, factor: 1000}}}}}},
          }}));
          // user switches to another entity -> auto-detection runs
          const afterFactor = changes[changes.length - 1];
          editor.shadowRoot.querySelectorAll('ha-form')[1].dispatchEvent(new CustomEvent('value-changed', {{
            detail: {{value: {{...shown, entity: 'sensor.e2e_prices'}}}},
          }}));
          await new Promise((r) => setTimeout(r, 200));
          return {{
            globalTitle: globalForm.data.title,
            shown,
            afterFactor,
            afterEntity: changes[changes.length - 1],
            schemaNames: sourceForm.schema.map((s) => s.name),
          }};
        }}
        """
    )
    assert "error" not in result, result
    assert result["globalTitle"] == "Stored title"
    # the stored configuration is shown as stored, not replaced by auto-detection
    assert result["shown"]["entity"] == "sensor.e2e_forecast"
    assert result["shown"]["value_key"] == "value"
    assert result["shown"]["extra_keys"] == ["outdoor_temp"]
    assert result["shown"]["detail_0"]["factor"] == 100
    assert result["shown"]["detail_0"]["name"] == "Preis"
    assert result["schemaNames"][:5] == [
        "entity",
        "attribute",
        "time_key",
        "value_key",
        "extra_keys",
    ]
    # edit keeps everything else
    values = result["afterFactor"]["sources"][0]["values"]
    assert values[0] == {"key": "value", "name": "Preis", "factor": 1000}
    assert values[1] == {"key": "outdoor_temp"}
    assert result["afterFactor"]["title"] == "Stored title"
    # new entity -> list attribute, time and value field are detected again
    assert result["afterEntity"]["sources"][0] == {
        "entity": "sensor.e2e_prices",
        "attribute": "data",
        "time_key": "start_time",
        "values": [{"key": "price_per_kwh"}],
    }
