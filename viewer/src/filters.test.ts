import { describe, expect, it } from "vitest";

import {
  emptyFilters,
  filterAndSortWorks,
  parseFilters,
  serializeFilters,
  workMatches,
  type FilterState,
} from "./filters";
import type { WorkCardRecord } from "./types";

function work(overrides: Partial<WorkCardRecord> = {}): WorkCardRecord {
  return {
    workId: "CME00099",
    displayTitle: "Recipes, Blessings, and Charms from Two Stockholm Manuscripts",
    preferredTitle: "Rezepte, Segen und Zaubersprüche",
    translatedTitle: "Recipes, Blessings, and Charms from Two Stockholm Manuscripts",
    author: "Anonymous contributors",
    editor: "Ferdinand Holthausen",
    dateDisplay: "Attested 1400–1597; published 1897",
    regionDisplay: "Norfolk, England",
    form: "mixed",
    languages: [
      { code: "enm", label: "Middle English" },
      { code: "lat", label: "Latin" },
    ],
    genres: [
      { term: "medical-recipe", label: "Medical recipe" },
      { term: "charm", label: "Charm" },
    ],
    subjects: [{ term: "medicine", label: "Medicine" }],
    tags: ["healing", "magic"],
    regions: [{ label: "Norfolk, England", relation: "dialect_region" }],
    sourcePeriods: ["15th century", "16th century"],
    publicationYear: 1897,
    summary: "A collection of medical recipes and protective charms.",
    metadataStatus: "cataloged",
    metadataRecordStatus: "partial",
    lineageStatus: "available",
    lastReviewed: "2026-07-11",
    publication: {
      status: "available",
      filename: "CME00099.pdf",
      path: "publication-pdfs/CME00099.pdf",
      externalUrl: null,
      bytes: 118649,
      sizeLabel: "116 KB",
      pages: 28,
      pageSize: "360 x 576 pts",
      embeddedTitle: null,
      embeddedAuthor: null,
      sha256: "abc",
    },
    detailPath: "catalog/works/CME00099.json",
    ...overrides,
  };
}

function filters(overrides: Partial<FilterState>): FilterState {
  return { ...emptyFilters, ...overrides };
}

describe("catalog filtering", () => {
  it("uses OR inside a facet and AND between facets", () => {
    const record = work();
    expect(
      workMatches(
        record,
        filters({ genres: ["romance", "charm"], languages: ["enm"] }),
      ),
    ).toBe(true);
    expect(
      workMatches(
        record,
        filters({ genres: ["romance", "charm"], languages: ["deu"] }),
      ),
    ).toBe(false);
  });

  it("searches human labels, identifiers, and accent-insensitive titles", () => {
    const record = work();
    expect(workMatches(record, filters({ query: "zauberspruche cme00099" }))).toBe(true);
    expect(workMatches(record, filters({ query: "middle english healing" }))).toBe(true);
    expect(workMatches(record, filters({ query: "Arthurian romance" }))).toBe(false);
  });

  it("sorts null publication years after dated records in both directions", () => {
    const undated = work({ workId: "B", displayTitle: "Undated", publicationYear: null });
    const old = work({ workId: "A", displayTitle: "Old", publicationYear: 1844 });
    const recent = work({ workId: "C", displayTitle: "Recent", publicationYear: 1929 });

    expect(
      filterAndSortWorks([undated, recent, old], filters({ sort: "publication-oldest" })).map(
        (item) => item.workId,
      ),
    ).toEqual(["A", "C", "B"]);
    expect(
      filterAndSortWorks([undated, old, recent], filters({ sort: "publication-newest" })).map(
        (item) => item.workId,
      ),
    ).toEqual(["C", "A", "B"]);
  });
});

describe("URL-backed filters", () => {
  it("round-trips repeated facets and ignores an unsupported sort", () => {
    const state = filters({
      query: "stockholm charms",
      sort: "title",
      genres: ["charm", "medical-recipe"],
      languages: ["enm"],
      sourcePeriods: ["15th century"],
    });
    expect(parseFilters(serializeFilters(state))).toEqual(state);

    const invalid = parseFilters(new URLSearchParams("sort=destructive&genre=charm"));
    expect(invalid.sort).toBe("catalog-order");
    expect(invalid.genres).toEqual(["charm"]);
  });
});
