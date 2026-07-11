import type { CatalogIndex, FacetOption } from "../types";
import {
  humanizeToken,
  multiFilterKeys,
  optionLabel,
  publicationYearFacets,
  type FilterState,
  type MultiFilterKey,
} from "../filters";

interface FacetGroupProps {
  title: string;
  filterKey: MultiFilterKey;
  options: FacetOption[];
  selected: string[];
  initiallyOpen?: boolean;
  onToggle: (key: MultiFilterKey, value: string) => void;
}

function FacetGroup({
  title,
  filterKey,
  options,
  selected,
  initiallyOpen = false,
  onToggle,
}: FacetGroupProps) {
  if (options.length === 0) return null;
  return (
    <details className="facet-group" open={initiallyOpen || selected.length > 0}>
      <summary>
        <span>{title}</span>
        {selected.length > 0 && (
          <span className="facet-selected-count">{selected.length}</span>
        )}
      </summary>
      <div className="facet-options">
        {options.map((option) => {
          const checked = selected.includes(option.value);
          return (
            <label className="facet-option" key={option.value}>
              <input
                type="checkbox"
                aria-label={optionLabel(option)}
                checked={checked}
                onChange={() => onToggle(filterKey, option.value)}
              />
              <span className="facet-option-label">{optionLabel(option)}</span>
              <span className="facet-option-count">{option.count}</span>
            </label>
          );
        })}
      </div>
    </details>
  );
}

interface FilterPanelProps {
  catalog: CatalogIndex;
  filters: FilterState;
  mobile?: boolean;
  onChange: (filters: FilterState) => void;
  onClear: () => void;
  onClose?: () => void;
}

const groups: Array<{
  title: string;
  key: Exclude<MultiFilterKey, "publicationYears">;
  facet: keyof CatalogIndex["facets"];
  open?: boolean;
}> = [
  {
    title: "Catalog coverage",
    key: "metadataStatuses",
    facet: "metadataStatuses",
    open: true,
  },
  {
    title: "PDF availability",
    key: "pdfStatuses",
    facet: "pdfStatuses",
  },
  { title: "Record status", key: "recordStatuses", facet: "recordStatuses" },
  { title: "Genre", key: "genres", facet: "genres", open: true },
  { title: "Subject", key: "subjects", facet: "subjects" },
  { title: "Language", key: "languages", facet: "languages", open: true },
  { title: "Form", key: "forms", facet: "forms" },
  { title: "Region", key: "regions", facet: "regions" },
  { title: "Source period", key: "sourcePeriods", facet: "sourcePeriods" },
  { title: "Tags", key: "tags", facet: "tags" },
];

export function FilterPanel({
  catalog,
  filters,
  mobile = false,
  onChange,
  onClear,
  onClose,
}: FilterPanelProps) {
  const toggle = (key: MultiFilterKey, value: string) => {
    const current = filters[key];
    onChange({
      ...filters,
      [key]: current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    });
  };

  const selectedCount = multiFilterKeys.reduce(
    (total, key) => total + filters[key].length,
    0,
  );

  return (
    <div className={mobile ? "filter-panel filter-panel-mobile" : "filter-panel"}>
      <div className="filter-panel-heading">
        <div>
          <p className="eyebrow">Refine the shelves</p>
          <h2>Filters</h2>
        </div>
        {mobile && (
          <button className="icon-button" type="button" onClick={onClose} autoFocus>
            <span aria-hidden="true">×</span>
            <span className="visually-hidden">Close filters</span>
          </button>
        )}
      </div>
      {selectedCount > 0 && (
        <button className="text-button clear-filter-button" type="button" onClick={onClear}>
          Clear {selectedCount} selected {selectedCount === 1 ? "filter" : "filters"}
        </button>
      )}
      <p className="filter-help">
        Match any checked value within a group, and every group you select.
      </p>

      {groups.map((group) => (
        <FacetGroup
          key={group.key}
          title={group.title}
          filterKey={group.key}
          options={catalog.facets[group.facet]}
          selected={filters[group.key]}
          initiallyOpen={group.open}
          onToggle={toggle}
        />
      ))}
      <FacetGroup
        title="Edition published"
        filterKey="publicationYears"
        options={publicationYearFacets(catalog)}
        selected={filters.publicationYears}
        onToggle={toggle}
      />

      {mobile && (
        <button className="button button-primary mobile-apply" type="button" onClick={onClose}>
          Show results
        </button>
      )}
    </div>
  );
}

interface ActiveFiltersProps {
  catalog: CatalogIndex;
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onClear: () => void;
}

export function ActiveFilters({
  catalog,
  filters,
  onChange,
  onClear,
}: ActiveFiltersProps) {
  const facetMaps = new Map<MultiFilterKey, Map<string, string>>();
  for (const group of groups) {
    facetMaps.set(
      group.key,
      new Map(
        catalog.facets[group.facet].map((option) => [
          option.value,
          optionLabel(option),
        ]),
      ),
    );
  }
  facetMaps.set(
    "publicationYears",
    new Map(publicationYearFacets(catalog).map((option) => [option.value, option.value])),
  );

  const chips = multiFilterKeys.flatMap((key) =>
    filters[key].map((value) => ({
      key,
      value,
      label: facetMaps.get(key)?.get(value) ?? humanizeToken(value),
    })),
  );
  if (!filters.query.trim() && chips.length === 0) return null;

  return (
    <div className="active-filters" aria-label="Active filters">
      {filters.query.trim() && (
        <button
          className="filter-chip"
          type="button"
          onClick={() => onChange({ ...filters, query: "" })}
        >
          Search: “{filters.query.trim()}” <span aria-hidden="true">×</span>
        </button>
      )}
      {chips.map((chip) => (
        <button
          className="filter-chip"
          type="button"
          key={`${chip.key}:${chip.value}`}
          onClick={() =>
            onChange({
              ...filters,
              [chip.key]: filters[chip.key].filter((item) => item !== chip.value),
            })
          }
        >
          {chip.label} <span aria-hidden="true">×</span>
        </button>
      ))}
      <button className="text-button" type="button" onClick={onClear}>
        Clear all
      </button>
    </div>
  );
}
