import { DEFAULTS, type CardConfig } from "./config";
import type { Series, SeriesResult } from "./series";

export interface Theme {
  text: string;
  grid: string;
}

export interface Figure {
  data: Array<Record<string, unknown>>;
  layout: Record<string, unknown>;
}

const formatters = new Map<string, Intl.DateTimeFormat>();

/** "YYYY-MM-DD HH:mm:ss" in the given IANA time zone, which Plotly renders as-is. */
export function toLocalString(ms: number, timeZone: string): string {
  let f = formatters.get(timeZone);
  if (!f) {
    f = new Intl.DateTimeFormat("sv-SE", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    formatters.set(timeZone, f);
  }
  return f.format(ms);
}

function axisTitle(series: Series[]): string {
  const units = [...new Set(series.map((s) => s.unit).filter(Boolean))];
  return units.join(" / ");
}

export function buildFigure(
  result: SeriesResult,
  config: CardConfig,
  theme: Theme,
  timeZone: string,
  now: number,
): Figure {
  const data = result.series.map((s) => ({
    type: "scatter",
    mode: "lines",
    name: s.name,
    x: s.t.map((t) => toLocalString(t, timeZone)),
    y: s.y,
    yaxis: s.axis === "right" ? "y2" : "y",
    line: { color: s.color, shape: s.shape, width: 2 },
    visible: s.visible ? true : "legendonly",
    hovertemplate: `%{fullData.name}: %{y:.4~g}${s.unit ? ` ${s.unit}` : ""}<extra></extra>`,
  }));

  const showLegend = config.show_legend ?? DEFAULTS.show_legend;
  const left = result.series.filter((s) => s.axis === "left");
  const right = result.series.filter((s) => s.axis === "right");
  const axisBase = {
    gridcolor: theme.grid,
    zerolinecolor: theme.grid,
    linecolor: theme.grid,
    tickfont: { color: theme.text },
    automargin: true,
  };
  const layout: Record<string, unknown> = {
    // room below the plot for the (two line) date labels and the horizontal legend
    margin: { l: 8, r: 8, t: 8, b: showLegend ? 92 : 8 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: theme.text },
    hovermode: "x unified",
    showlegend: showLegend,
    legend: { orientation: "h", x: 0, y: -0.2, yanchor: "top" },
    xaxis: { ...axisBase, type: "date" },
    yaxis: { ...axisBase, title: { text: axisTitle(left) } },
  };
  if (right.length) {
    layout.yaxis2 = {
      ...axisBase,
      overlaying: "y",
      side: "right",
      showgrid: false,
      title: { text: axisTitle(right) },
    };
  }
  if (config.show_now ?? DEFAULTS.show_now) {
    layout.shapes = [
      {
        type: "line",
        xref: "x",
        yref: "paper",
        x0: toLocalString(now, timeZone),
        x1: toLocalString(now, timeZone),
        y0: 0,
        y1: 1,
        line: { color: theme.text, width: 1, dash: "dot" },
        opacity: 0.6,
      },
    ];
  }
  return { data, layout };
}
