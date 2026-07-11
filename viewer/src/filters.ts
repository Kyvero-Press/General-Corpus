import type { CatalogIndex, FacetOption, WorkCardRecord } from "./types";

export const sortValues = [
  "catalog-order",
  "title",
  "author",
  "publication-oldest",
  "publication-newest",
] as const;

export type SortValue = (typeof sortValues)[number];

export interface FilterState {
  query: string;
  sort: SortValue;
  metadataStatuses: string[];
  pdfStatuses: string[];
  recordStatuses: string[];
  forms: string[];
  languages: string[];
  genres: string[];
  subjects: string[];
  tags: string[];
  regions: string[];
  sourcePeriods: string[];
  publicationYears: string[];
}

export type MultiFilterKey = Exclude<keyof FilterState, "query" | "sort">;

export const emptyFilters: FilterState = {
  query: "",
  sort: "catalog-order",
  metadataStatuses: [],
  pdfStatuses: [],
  recordStatuses: [],
  forms: [],
  languages: [],
  genres: [],
  subjects: [],
  tags: [],
  regions: [],
  sourcePeriods: [],
  publicationYears: [],
};

const queryKeys: Record<MultiFilterKey, string> = {
  metadataStatuses: "metadata",
  pdfStatuses: "pdf",
  recordStatuses: "record",
  forms: "form",
  languages: "language",
  genres: "genre",
  subjects: "subject",
  tags: "tag",
  regions: "region",
  sourcePeriods: "period",
  publicationYears: "year",
};

export const multiFilterKeys = Object.keys(queryKeys) as MultiFilterKey[];

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

export function parseFilters(parameters: URLSearchParams): FilterState {
  const requestedSort = parameters.get("sort");
  const result: FilterState = {
    ...emptyFilters,
    query: parameters.get("q")?.trim() ?? "",
    sort: sortValues.includes(requestedSort as SortValue)
      ? (requestedSort as SortValue)
      : "catalog-order",
  };
  for (const key of multiFilterKeys) {
    result[key] = unique(parameters.getAll(queryKeys[key]));
  }
  return result;
}

export function serializeFilters(filters: FilterState): URLSearchParams {
  const parameters = new URLSearchParams();
  if (filters.query.trim()) parameters.set("q", filters.query.trim());
  if (filters.sort !== "catalog-order") parameters.set("sort", filters.sort);
  for (const key of multiFilterKeys) {
    for (const value of filters[key]) parameters.append(queryKeys[key], value);
  }
  return parameters;
}

function normalize(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase();
}

function hasSelected(selected: string[], actual: string[]): boolean {
  return selected.length === 0 || selected.some((value) => actual.includes(value));
}

function searchText(work: WorkCardRecord): string {
  return normalize(
    [
      work.workId,
      work.displayTitle,
      work.preferredTitle,
      work.author,
      work.editor ?? "",
      work.dateDisplay,
      work.regionDisplay,
      work.summary,
      work.form,
      ...work.languages.flatMap((item) => [item.code, item.label]),
      ...work.genres.flatMap((item) => [item.term, item.label]),
      ...work.subjects.flatMap((item) => [item.term, item.label]),
      ...work.tags,
      ...work.sourcePeriods,
    ].join(" "),
  );
}

export function workMatches(work: WorkCardRecord, filters: FilterState): boolean {
  const terms = normalize(filters.query).split(/\s+/).filter(Boolean);
  const haystack = terms.length ? searchText(work) : "";
  return (
    terms.every((term) => haystack.includes(term)) &&
    hasSelected(filters.metadataStatuses, [work.metadataStatus]) &&
    hasSelected(filters.pdfStatuses, [work.publication.status]) &&
    hasSelected(
      filters.recordStatuses,
      work.metadataRecordStatus ? [work.metadataRecordStatus] : [],
    ) &&
    hasSelected(filters.forms, [work.form]) &&
    hasSelected(
      filters.languages,
      work.languages.map((item) => item.code),
    ) &&
    hasSelected(
      filters.genres,
      work.genres.map((item) => item.term),
    ) &&
    hasSelected(
      filters.subjects,
      work.subjects.map((item) => item.term),
    ) &&
    hasSelected(filters.tags, work.tags) &&
    hasSelected(
      filters.regions,
      work.regions.map((item) => item.label),
    ) &&
    hasSelected(filters.sourcePeriods, work.sourcePeriods) &&
    hasSelected(
      filters.publicationYears,
      work.publicationYear === null ? [] : [String(work.publicationYear)],
    )
  );
}

function compareNullableNumber(
  left: number | null,
  right: number | null,
  direction: 1 | -1,
): number {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return (left - right) * direction;
}

export function filterAndSortWorks(
  works: WorkCardRecord[],
  filters: FilterState,
): WorkCardRecord[] {
  const selected = works.filter((work) => workMatches(work, filters));
  if (filters.sort === "catalog-order") return selected;
  return [...selected].sort((left, right) => {
    if (filters.sort === "title") {
      return left.displayTitle.localeCompare(right.displayTitle, undefined, {
        sensitivity: "base",
      });
    }
    if (filters.sort === "author") {
      return (
        left.author.localeCompare(right.author, undefined, {
          sensitivity: "base",
        }) || left.displayTitle.localeCompare(right.displayTitle)
      );
    }
    return compareNullableNumber(
      left.publicationYear,
      right.publicationYear,
      filters.sort === "publication-oldest" ? 1 : -1,
    );
  });
}

export function selectedFilterCount(filters: FilterState): number {
  return (
    (filters.query.trim() ? 1 : 0) +
    multiFilterKeys.reduce((total, key) => total + filters[key].length, 0)
  );
}

export function publicationYearFacets(catalog: CatalogIndex): FacetOption[] {
  const counts = new Map<string, number>();
  for (const work of catalog.works) {
    if (work.publicationYear !== null) {
      const value = String(work.publicationYear);
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
  }
  return [...counts]
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([value, count]) => ({ value, count }));
}

export function optionLabel(option: FacetOption): string {
  return option.label ?? humanizeToken(option.value);
}

export function humanizeToken(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const text = value.replace(/[_-]+/g, " ");
  return text.charAt(0).toLocaleUpperCase() + text.slice(1);
}
