import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkCard } from "./components/WorkCard";
import type { WorkCardRecord } from "./types";

const lineageOnlyWork: WorkCardRecord = {
  workId: "LineageOnly",
  displayTitle: "A Lineage-only Work",
  preferredTitle: "A Lineage-only Work",
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
  summary: "Descriptive metadata pending.",
  metadataStatus: "pending",
  metadataRecordStatus: null,
  lineageStatus: "available",
  lastReviewed: null,
  publication: {
    status: "unavailable",
    filename: "LineageOnly.pdf",
    path: null,
    externalUrl: null,
    bytes: null,
    sizeLabel: null,
    pages: null,
    pageSize: null,
    embeddedTitle: null,
    embeddedAuthor: null,
    sha256: null,
  },
  detailPath: "catalog/works/LineageOnly.json",
};

describe("WorkCard", () => {
  it("keeps lineage status independent from pending descriptive metadata", () => {
    render(<WorkCard work={lineageOnlyWork} onOpen={vi.fn()} />);
    expect(screen.getByText("Metadata pending")).toBeInTheDocument();
    expect(screen.getByText("Sources linked")).toBeInTheDocument();
    expect(screen.getByText(/separately researched source lineage is available/i)).toBeInTheDocument();
    expect(screen.queryByText(/source lineage have not yet been cataloged/i)).not.toBeInTheDocument();
  });
});
