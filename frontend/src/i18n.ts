import type { ErrorCode } from "./series";

type Dict = Record<string, string>;

const en: Dict = {
  title: "Title",
  height: "Height (px)",
  time_range: "Time range",
  time_range_all: "Whole forecast",
  time_range_from_now: "From now on",
  show_now: "Show \"now\" marker",
  show_legend: "Show legend",
  sources: "Series sources",
  add_source: "Add entity",
  remove: "Remove",
  move_up: "Move up",
  move_down: "Move down",
  entity: "Entity",
  attribute: "List attribute",
  time_key: "Time field",
  value_key: "Value field",
  extra_keys: "Additional value fields",
  details: "Details",
  name: "Name",
  color: "Color",
  factor: "Scaling factor",
  offset: "Offset",
  unit: "Unit",
  shape: "Line shape",
  shape_hv: "Steps",
  shape_linear: "Linear",
  axis: "Y axis",
  axis_auto: "Automatic",
  axis_left: "Left",
  axis_right: "Right",
  visible: "Visible",
  empty: "No series configured yet. Open the card editor and add an entity.",
  pick_entity: "Pick an entity",
  entity_missing: "Entity not found",
  entity_unavailable: "Entity is unavailable",
  attribute_missing: "No list attribute found",
  time_missing: "Time field not found",
  value_missing: "No numeric value field found",
  no_data: "No usable data points",
};

const de: Dict = {
  title: "Titel",
  height: "Höhe (px)",
  time_range: "Zeitbereich",
  time_range_all: "Gesamter Forecast",
  time_range_from_now: "Ab jetzt",
  show_now: "„Jetzt“-Marker anzeigen",
  show_legend: "Legende anzeigen",
  sources: "Serien-Quellen",
  add_source: "Entität hinzufügen",
  remove: "Entfernen",
  move_up: "Nach oben",
  move_down: "Nach unten",
  entity: "Entität",
  attribute: "Listen-Attribut",
  time_key: "Zeitfeld",
  value_key: "Wertefeld",
  extra_keys: "Weitere Wertefelder",
  details: "Details",
  name: "Name",
  color: "Farbe",
  factor: "Skalierungsfaktor",
  offset: "Offset",
  unit: "Einheit",
  shape: "Linienform",
  shape_hv: "Stufen",
  shape_linear: "Linear",
  axis: "Y-Achse",
  axis_auto: "Automatisch",
  axis_left: "Links",
  axis_right: "Rechts",
  visible: "Sichtbar",
  empty: "Noch keine Serie konfiguriert. Öffne den Karten-Editor und füge eine Entität hinzu.",
  pick_entity: "Entität auswählen",
  entity_missing: "Entität nicht gefunden",
  entity_unavailable: "Entität ist nicht verfügbar",
  attribute_missing: "Kein Listen-Attribut gefunden",
  time_missing: "Zeitfeld nicht gefunden",
  value_missing: "Kein numerisches Wertefeld gefunden",
  no_data: "Keine verwertbaren Datenpunkte",
};

const dicts: Record<string, Dict> = { en, de };

export type Translate = (key: string) => string;

export function translator(language: string | undefined): Translate {
  const dict = dicts[(language ?? "en").slice(0, 2).toLowerCase()] ?? en;
  return (key) => dict[key] ?? en[key] ?? key;
}

export const errorKey = (code: ErrorCode): string => code;
