import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type {
  CatalogIndex,
  WorkCardRecord,
  WorkDetailRecord,
} from "./types";

const publication = {
  status: "available" as const,
  filename: "CME00099.pdf",
  path: "publication-pdfs/CME00099.pdf",
  externalUrl: null,
  bytes: 118649,
  sizeLabel: "116 KB",
  pages: 28,
  pageSize: "360 x 576 pts",
  embeddedTitle: "Recipes",
  embeddedAuthor: "Anonymous",
  sha256: "abc123",
};

const catalogedWork: WorkCardRecord = {
  workId: "CME00099",
  displayTitle: "Recipes, Blessings, and Charms from Two Stockholm Manuscripts",
  preferredTitle: "Rezepte, Segen und Zaubersprüche",
  translatedTitle: "Recipes, Blessings, and Charms from Two Stockholm Manuscripts",
  author: "Anonymous contributors",
  editor: "Ferdinand Holthausen",
  dateDisplay: "Attested 1400–1597; published 1897",
  regionDisplay: "Norfolk, England",
  form: "mixed",
  languages: [{ code: "enm", label: "Middle English" }],
  genres: [{ term: "charm", label: "Charm" }],
  subjects: [{ term: "medicine", label: "Medicine" }],
  tags: ["medical", "magic"],
  regions: [{ label: "Norfolk, England", relation: "dialect_region" }],
  sourcePeriods: ["15th century"],
  publicationYear: 1897,
  summary: "Thirty-one medical recipes, blessings, and charms.",
  metadataStatus: "cataloged",
  metadataRecordStatus: "partial",
  lineageStatus: "available",
  lastReviewed: "2026-07-11",
  publication,
  detailPath: "catalog/works/CME00099.json",
};

const pendingWork: WorkCardRecord = {
  ...catalogedWork,
  workId: "Gawain",
  displayTitle: "Sir Gawain and the Green Knight",
  preferredTitle: "Sir Gawain and the Green Knight",
  translatedTitle: null,
  author: "Anonymous",
  editor: null,
  dateDisplay: "Descriptive metadata pending",
  regionDisplay: "Region metadata pending",
  form: "unknown",
  languages: [],
  genres: [],
  subjects: [],
  tags: [],
  regions: [],
  sourcePeriods: [],
  publicationYear: null,
  summary: "A generated General Corpus publication awaiting a descriptive metadata manifest.",
  metadataStatus: "pending",
  metadataRecordStatus: null,
  lineageStatus: "missing",
  lastReviewed: null,
  publication: { ...publication, filename: "Gawain.pdf", path: "publication-pdfs/Gawain.pdf" },
  detailPath: "catalog/works/Gawain.json",
};

const catalog: CatalogIndex = {
  schemaVersion: "1.0.0",
  catalogReviewedThrough: "2026-07-11",
  metadataReviewedThrough: "2026-07-11",
  lineageReviewedThrough: "2026-07-11",
  coverageNote: "Incremental",
  lineageCoverageNote: "Incremental",
  publicationInventory: null,
  counts: {
    works: 2,
    catalogedMetadata: 1,
    lineageRecords: 1,
    metadataPending: 1,
    pdfsAvailable: 2,
    pdfsUnavailable: 0,
    publicationBytes: 237298,
  },
  facets: {
    metadataStatuses: [
      { value: "cataloged", count: 1 },
      { value: "pending", count: 1 },
    ],
    pdfStatuses: [{ value: "available", count: 2 }],
    recordStatuses: [{ value: "partial", count: 1 }],
    forms: [{ value: "mixed", count: 1 }],
    languages: [{ value: "enm", label: "Middle English", count: 1 }],
    genres: [{ value: "charm", label: "Charm", count: 1 }],
    subjects: [{ value: "medicine", label: "Medicine", count: 1 }],
    tags: [
      { value: "magic", count: 1 },
      { value: "medical", count: 1 },
    ],
    regions: [{ value: "Norfolk, England", count: 1 }],
    sourcePeriods: [{ value: "15th century", count: 1 }],
  },
  works: [catalogedWork, pendingWork],
};

const detail: WorkDetailRecord = {
  schemaVersion: "1.0.0",
  work: catalogedWork,
  metadata: null,
  lineage: {
    manifestId: "lineage:CME00099",
    recordStatus: "partial",
    lastReviewed: "2026-07-11",
    summary: "The repository XML was encoded from Holthausen’s 1897 edition.",
    entities: [
      {
        id: "edition:holthausen",
        type: "scholarly_edition",
        label: "Holthausen’s 1897 edition",
        description: "The immediate print source.",
        identifiers: [],
        bibliographic: null,
        holding: null,
        physicalDescription: null,
        dateStatements: [],
        survivalStatus: "extant",
        notes: [],
        access: [
          {
            id: "access:scan",
            entityId: "edition:holthausen",
            entityLabel: "Holthausen’s 1897 edition",
            entityType: "scholarly_edition",
            provider: "Internet Archive",
            resourceKind: "page_images",
            status: "publicly_available",
            accessMethod: "Public page images",
            url: "https://example.test/holthausen",
            alternateUrls: ["https://example.test/holthausen.pdf"],
            contact: null,
            cost: "free",
            format: "PDF",
            lastChecked: "2026-07-11",
            notes: [],
            localCopies: [{
              label: "Complete Holthausen PDF",
              path: "source-cache/CME00099/holthausen.pdf",
              sourceUrl: "https://example.test/holthausen.pdf",
              sha256: "a".repeat(64),
              bytes: 2048,
              sizeLabel: "2.0 KiB",
              mediaType: "application/pdf",
              downloadedOn: "2026-07-11",
              coverage: "complete",
              workPortion: {
                label: "Recipes in KB X 90",
                locators: ["manuscript pages 12–21", "digital images 16–25"],
                startUrl: "https://example.test/x90/image/16",
                endUrl: "https://example.test/x90/image/25",
                notes: ["The cached file contains the complete manuscript."],
              },
              notes: [],
              available: true,
            }],
            rights: [],
          },
        ],
        rights: [
          {
            id: "rights:edition",
            entity: "edition:holthausen",
            component: "The 1897 edition and editorial text",
            jurisdiction: "United States",
            copyright_status: "public_domain",
            as_of: "2026-07-11",
            basis: "Published in 1897.",
          },
        ],
      },
    ],
    relations: [
      {
        id: "relation:encoded",
        type: "encoded_from",
        subjectId: "encoding:cme",
        subjectLabel: "CME digital text",
        objectId: "edition:holthausen",
        objectLabel: "Holthausen’s 1897 edition",
        scope: {
          subject: { kind: "whole", description: "The complete CME digital text" },
          object: {
            kind: "part",
            description: "Holthausen’s printed pages 75–88",
            locators: ["printed pages 75–88"],
          },
        },
        assertion: { status: "confirmed", confidence: "high" },
      },
    ],
    sourceLinks: [],
    openQuestions: [],
    reviewNotes: [],
  },
  metadataManifestPath: "catalog/manifests/work-metadata/CME00099.json",
  lineageManifestPath: "catalog/manifests/lineage/CME00099.json",
};

function response(value: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => value,
  } as Response;
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("catalog/index.json")) return response(catalog);
        if (url.includes("catalog/works/CME00099.json")) return response(detail);
        throw new Error(`Unexpected fetch: ${url}`);
      }),
    );
  });

  it("browses and filters human-readable work cards", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Sir Gawain and the Green Knight")).toBeInTheDocument();
    expect(screen.getByText("Recipes, Blessings, and Charms from Two Stockholm Manuscripts")).toBeInTheDocument();
    expect(screen.getByText("2 works")).toBeInTheDocument();
    expect(screen.queryByText("Books with their sources in view.")).not.toBeInTheDocument();
    expect(within(screen.getByLabelText("Catalog totals")).getAllByText("2")).toHaveLength(2);

    const filters = screen.getByRole("complementary", { name: "Catalog filters" });
    await user.click(within(filters).getByRole("checkbox", { name: /Cataloged/ }));
    expect(screen.getByText("1 work")).toBeInTheDocument();
    expect(screen.queryByText("Sir Gawain and the Green Knight")).not.toBeInTheDocument();
    expect(window.location.search).toContain("metadata=cataloged");
  });

  it("opens a work record with PDF, lineage source, rights, and raw manifests", async () => {
    const user = userEvent.setup();
    render(<App />);

    const title = await screen.findByRole("button", {
      name: "Recipes, Blessings, and Charms from Two Stockholm Manuscripts",
    });
    await user.click(title);

    const dialog = await screen.findByRole("dialog", {
      name: "Recipes, Blessings, and Charms from Two Stockholm Manuscripts",
    });
    expect(within(dialog).getByText("Known sources and access routes")).toBeInTheDocument();
    expect(
      within(dialog).getByRole("heading", { name: "Holthausen’s 1897 edition" }),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: /View page images/ })).toHaveAttribute(
      "href",
      "https://example.test/holthausen",
    );
    expect(within(dialog).getByText("Downloaded locally")).toBeInTheDocument();
    expect(
      within(dialog).getByText("Checksum-verified local copy: Complete Holthausen PDF"),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: /Exact file download/ })).toHaveAttribute(
      "href",
      "https://example.test/holthausen.pdf",
    );
    expect(within(dialog).getByText("Work location within source: Recipes in KB X 90")).toBeInTheDocument();
    expect(within(dialog).getByText("manuscript pages 12–21")).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: /Open work start/ })).toHaveAttribute(
      "href",
      "https://example.test/x90/image/16",
    );
    expect(within(dialog).getByText("The complete CME digital text")).toBeInTheDocument();
    expect(within(dialog).getByText("Holthausen’s printed pages 75–88")).toBeInTheDocument();
    expect(within(dialog).getByText("The 1897 edition and editorial text")).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "Descriptive metadata JSON" })).toHaveAttribute(
      "href",
      expect.stringContaining("catalog/manifests/work-metadata/CME00099.json"),
    );
    expect(within(dialog).getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "download",
      "CME00099.pdf",
    );
    expect(window.location.hash).toBe("#work=CME00099");
    await user.click(within(dialog).getByRole("button", { name: "Sources" }));
    expect(window.location.hash).toBe("#work=CME00099");
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: /Close/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(title).toHaveFocus();
  });

  it("keeps mobile filters modal and restores the trigger on Escape", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Sir Gawain and the Green Knight");
    const trigger = screen.getByRole("button", { name: "Filters" });
    await user.click(trigger);

    const dialog = screen.getByRole("dialog", { name: "Catalog filters" });
    const close = within(dialog).getByRole("button", { name: "Close filters" });
    expect(close).toHaveFocus();
    expect(document.querySelector(".site-header")).toHaveProperty("inert", true);

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Catalog filters" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("reloads a plus-sign work from an encoded deep link without changing static paths", async () => {
    const plusWork: WorkCardRecord = {
      ...pendingWork,
      workId: "Vices+V1",
      displayTitle: "Vices and Virtues, Volume I",
      preferredTitle: "Vices and Virtues, Volume I",
      detailPath: "catalog/works/Vices+V1.json",
      publication: {
        ...pendingWork.publication,
        filename: "Vices+V1.pdf",
        path: "publication-pdfs/Vices+V1.pdf",
      },
    };
    const plusCatalog: CatalogIndex = {
      ...catalog,
      counts: { ...catalog.counts, works: 1, metadataPending: 1, catalogedMetadata: 0 },
      works: [plusWork],
    };
    const plusDetail: WorkDetailRecord = {
      schemaVersion: "1.0.0",
      work: plusWork,
      metadata: null,
      lineage: null,
      metadataManifestPath: null,
      lineageManifestPath: null,
    };
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("catalog/index.json")) return response(plusCatalog);
      if (url.includes("catalog/works/Vices+V1.json")) return response(plusDetail);
      throw new Error(`Unexpected fetch: ${url}`);
    });
    window.history.replaceState(null, "", "/#work=Vices%2BV1");

    render(<App />);
    const dialog = await screen.findByRole("dialog", {
      name: "Vices and Virtues, Volume I",
    });
    expect(window.location.hash).toBe("#work=Vices%2BV1");
    expect(within(dialog).getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      expect.stringContaining("publication-pdfs/Vices+V1.pdf"),
    );
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.stringContaining("catalog/works/Vices+V1.json"),
      expect.any(Object),
    );
  });
});
