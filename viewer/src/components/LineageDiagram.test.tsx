import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LineageEntity, LineageRelation } from "../types";
import {
  buildLineageForest,
  duplicateEntityLabelIds,
  isPrimaryTransmissionRelation,
  partitionLineageRelations,
} from "../lineage";
import { LineageDiagram } from "./LineageDiagram";

function entity(id: string, label: string, type = "manuscript_witness"): LineageEntity {
  return {
    id,
    label,
    type,
    description: null,
    identifiers: [],
    bibliographic: null,
    holding: null,
    physicalDescription: null,
    dateStatements: [],
    survivalStatus: "extant",
    notes: [],
    access: [],
    rights: [],
  };
}

function relation(
  id: string,
  type: string,
  subjectId: string | null,
  objectId: string | null,
  subjectLabel: string,
  objectLabel: string,
): LineageRelation {
  return {
    id,
    type,
    subjectId,
    subjectLabel,
    objectId,
    objectLabel,
    scope: null,
    assertion: { status: "confirmed", confidence: "high" },
  };
}

describe("lineage diagram model", () => {
  it("builds a stable branching forest, marks shared nodes, and guards cycles", () => {
    const entities = [
      entity("artifact", "Repository PDF", "repository_artifact"),
      entity("encoding", "Digital encoding", "digital_encoding"),
      entity("edition", "Printed edition", "scholarly_edition"),
      entity("comparison", "Comparison edition", "scholarly_edition"),
      entity("witness", "Manuscript witness"),
    ];
    const relations = [
      relation("r1", "copied_from", "artifact", "encoding", "Repository PDF", "Digital encoding"),
      relation("r2", "encoded_from", "encoding", "edition", "Digital encoding", "Printed edition"),
      relation("r3", "transcribes", "edition", "witness", "Printed edition", "Manuscript witness"),
      relation("r4", "transcribes", "comparison", "witness", "Comparison edition", "Manuscript witness"),
      relation("r5", "same_as", "witness", "witness", "Manuscript witness", "Manuscript witness"),
      relation("invalid", "describes", null, "witness", "Missing", "Manuscript witness"),
    ];

    const forest = buildLineageForest(entities, relations);
    expect(forest.nodeCount).toBe(5);
    expect(forest.relationCount).toBe(5);
    expect(forest.omittedRelationCount).toBe(1);
    expect(forest.roots.map((root) => root.id)).toEqual(["artifact", "comparison"]);

    const encoding = forest.roots[0].branches[0].target;
    const edition = encoding.branches[0].target;
    const witness = edition.branches[0].target;
    expect(witness.branches[0].target.cycle).toBe(true);
    expect(forest.roots[1].branches[0].target.reference).toBe(true);
  });

  it("classifies excerpting as direct transmission but facsimiles as supporting", () => {
    expect(
      isPrimaryTransmissionRelation(
        relation("excerpt", "excerpted_from", "edition", "witness", "Edition", "Witness"),
      ),
    ).toBe(true);
    expect(
      isPrimaryTransmissionRelation(
        relation("facsimile", "facsimile_of", "scan", "witness", "Scan", "Witness"),
      ),
    ).toBe(false);
  });

  it("identifies colliding source labels for exact-ID disambiguation", () => {
    const entities = [
      entity("witness:one", "Accounts 1378-9"),
      entity("witness:two", "Accounts 1378-9"),
      entity("witness:three", "Accounts 1379-80"),
    ];
    expect([...duplicateEntityLabelIds(entities)]).toEqual(["witness:one", "witness:two"]);
  });

  it("keeps disconnected direct edges out of the repository artifact's primary path", () => {
    const entities = [
      entity("artifact", "Repository XML", "repository_artifact"),
      entity("encoding", "Digital encoding", "digital_encoding"),
      entity("edition", "Immediate edition", "scholarly_edition"),
      entity("prior", "Prior edition", "scholarly_edition"),
      entity("witness", "Witness"),
    ];
    const partition = partitionLineageRelations(entities, [
      relation("r1", "copied_from", "artifact", "encoding", "Repository XML", "Digital encoding"),
      relation("r2", "encoded_from", "encoding", "edition", "Digital encoding", "Immediate edition"),
      relation("r3", "transcribes", "prior", "witness", "Prior edition", "Witness"),
      relation("r4", "collated_against", "edition", "witness", "Immediate edition", "Witness"),
    ]);

    expect(partition.primary.map((item) => item.id)).toEqual(["r1", "r2"]);
    expect(partition.otherTransmission.map((item) => item.id)).toEqual(["r3"]);
    expect(partition.supporting.map((item) => item.id)).toEqual(["r4"]);
  });

  it("follows direct edges from an encoding linked to the artifact by a qualified version relation", () => {
    const entities = [
      entity("artifact", "Repository XML", "repository_artifact"),
      entity("encoding", "Digital encoding", "digital_encoding"),
      entity("edition", "Immediate edition", "scholarly_edition"),
      entity("other-encoding", "Unrelated encoding", "digital_encoding"),
      entity("other-edition", "Unrelated edition", "scholarly_edition"),
    ];
    const partition = partitionLineageRelations(entities, [
      relation("bridge", "version_of", "artifact", "encoding", "Repository XML", "Digital encoding"),
      relation("source", "encoded_from", "encoding", "edition", "Digital encoding", "Immediate edition"),
      relation(
        "unrelated",
        "encoded_from",
        "other-encoding",
        "other-edition",
        "Unrelated encoding",
        "Unrelated edition",
      ),
    ]);

    expect(partition.primary.map((item) => item.id)).toEqual(["source"]);
    expect(partition.otherTransmission.map((item) => item.id)).toEqual(["unrelated"]);
    expect(partition.supporting.map((item) => item.id)).toEqual(["bridge"]);
  });

  it("uses the manifest primary subject rather than contextual repository artifacts as roots", () => {
    const entities = [
      entity("artifact:corpus", "Corpus XML", "repository_artifact"),
      entity("artifact:transcript", "Historical transcript", "repository_artifact"),
      entity("encoding", "Digital encoding", "digital_encoding"),
      entity("witness", "Witness"),
    ];
    const partition = partitionLineageRelations(
      entities,
      [
        relation("corpus", "copied_from", "artifact:corpus", "encoding", "Corpus XML", "Digital encoding"),
        relation(
          "context",
          "transcribes",
          "artifact:transcript",
          "witness",
          "Historical transcript",
          "Witness",
        ),
      ],
      "artifact:corpus",
    );

    expect(partition.primary.map((item) => item.id)).toEqual(["corpus"]);
    expect(partition.otherTransmission.map((item) => item.id)).toEqual(["context"]);
  });

  it("does not use a merely descriptive artifact-to-encoding edge as a traversal bridge", () => {
    const entities = [
      entity("artifact", "Corpus XML", "repository_artifact"),
      entity("encoding", "Contextual encoding", "digital_encoding"),
      entity("edition", "Contextual edition", "scholarly_edition"),
    ];
    const partition = partitionLineageRelations(
      entities,
      [
        relation("description", "describes", "artifact", "encoding", "Corpus XML", "Contextual encoding"),
        relation("source", "encoded_from", "encoding", "edition", "Contextual encoding", "Contextual edition"),
      ],
      "artifact",
    );

    expect(partition.primary).toHaveLength(0);
    expect(partition.otherTransmission.map((item) => item.id)).toEqual(["source"]);
    expect(partition.supporting.map((item) => item.id)).toEqual(["description"]);
  });

  it("honors an explicit reviewed path without changing mixed relation semantics", () => {
    const entities = [
      entity("artifact", "Corpus XML", "repository_artifact"),
      entity("encoding", "Source package", "digital_encoding"),
      entity("facsimile", "Page-image set", "facsimile"),
      entity("carrier", "Journal volume", "physical_edition"),
      entity("article", "Scholarly article", "scholarly_edition"),
      entity("witness", "Manuscript witness"),
      entity("catalog", "Catalog record", "catalog_record"),
    ];
    const relations = [
      relation("r1", "version_of", "artifact", "encoding", "Corpus XML", "Source package"),
      relation("r2", "contains", "encoding", "facsimile", "Source package", "Page-image set"),
      relation("r3", "facsimile_of", "facsimile", "carrier", "Page-image set", "Journal volume"),
      relation("r4", "contains", "carrier", "article", "Journal volume", "Scholarly article"),
      relation("r5", "transcribes", "article", "witness", "Scholarly article", "Manuscript witness"),
      relation("r6", "describes", "catalog", "witness", "Catalog record", "Manuscript witness"),
    ];

    const partition = partitionLineageRelations(
      entities,
      relations,
      "artifact",
      {
        primaryTransmissionPaths: [{
          id: "path:reviewed",
          label: "Reviewed production path",
          relationIds: ["r1", "r2", "r3", "r4", "r5"],
          entitySequence: ["artifact", "encoding", "facsimile", "carrier", "article", "witness"],
          description: "The reviewed path preserves each relationship's exact meaning.",
        }],
        supportingRelationships: [{
          id: "group:catalog",
          label: "Catalog support",
          relationIds: ["r6"],
          description: "The catalog describes the witness but is not a production step.",
        }],
      },
    );

    expect(partition.primary.map((item) => item.id)).toEqual(["r1", "r2", "r3", "r4", "r5"]);
    expect(partition.otherTransmission).toEqual([]);
    expect(partition.supporting.map((item) => item.id)).toEqual(["r6"]);
  });
});

describe("LineageDiagram", () => {
  it("renders a semantic path and links known nodes to their source cards", async () => {
    const user = userEvent.setup();
    const scrollIntoView = vi.fn();
    const target = document.createElement("article");
    target.id = "source-edition%3A1897";
    target.tabIndex = -1;
    target.scrollIntoView = scrollIntoView;
    document.body.append(target);

    render(
      <LineageDiagram
        title="Primary transmission paths"
        entities={[
          entity("encoding:cme", "CME digital text", "digital_encoding"),
          entity("edition:1897", "The 1897 edition", "scholarly_edition"),
        ]}
        relations={[
          relation(
            "encoded",
            "encoded_from",
            "encoding:cme",
            "edition:1897",
            "CME digital text",
            "The 1897 edition",
          ),
        ]}
      />,
    );

    expect(
      screen.getByRole("figure", { name: "Primary transmission paths" }),
    ).toHaveTextContent("2 source records · 1 relationship");
    expect(screen.getByText("Encoded from")).toBeInTheDocument();
    const sourceLink = screen.getByRole("link", {
      name: /View source details: The 1897 edition\. Scholarly edition\./,
    });
    expect(sourceLink).toHaveAttribute("href", "#source-edition%3A1897");

    await user.click(sourceLink);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "start" });
    expect(target).toHaveFocus();
    target.remove();
  });

  it("summarizes large fan-outs until the reader expands them", async () => {
    const user = userEvent.setup();
    const witnesses = Array.from({ length: 443 }, (_, index) =>
      entity(`witness:${index}`, `Witness ${index + 1}`),
    );
    render(
      <LineageDiagram
        title="Primary transmission paths"
        entities={[entity("edition", "Large source edition", "scholarly_edition"), ...witnesses]}
        relations={witnesses.map((item, index) =>
          relation(
            `relation:${index}`,
            "transcribes",
            "edition",
            item.id,
            "Large source edition",
            item.label ?? item.id,
          ),
        )}
      />,
    );

    expect(screen.getByText("443 relationships")).toBeInTheDocument();
    expect(screen.queryByText("Witness 443")).not.toBeInTheDocument();
    await user.click(screen.getByText("443 relationships"));
    expect(await screen.findByText("Witness 443")).toBeInTheDocument();
  });

  it("condenses repeated endpoint edges while preserving their scoped relationship count", () => {
    const lowerCertainty = relation(
      "scope:two",
      "transcribes",
      "edition",
      "witness",
      "Source edition",
      "Shared witness",
    );
    lowerCertainty.assertion = { status: "supported", confidence: "medium" };
    render(
      <LineageDiagram
        title="Primary transmission paths"
        entities={[
          entity("edition", "Source edition", "scholarly_edition"),
          entity("witness", "Shared witness"),
        ]}
        relations={[
          relation("scope:one", "transcribes", "edition", "witness", "Source edition", "Shared witness"),
          lowerCertainty,
        ]}
      />,
    );

    expect(screen.getByText("2 scoped relationships")).toBeInTheDocument();
    expect(screen.getByText("Mixed certainty")).toBeInTheDocument();
    expect(screen.getAllByText("Shared witness")).toHaveLength(1);
  });

  it("keeps branches with downstream relationships visible outside collapsed fan-outs", () => {
    const leaves = Array.from({ length: 12 }, (_, index) =>
      entity(`leaf:${index}`, `Leaf ${index + 1}`),
    );
    render(
      <LineageDiagram
        title="Supporting relationships"
        entities={[
          entity("edition", "Edition", "scholarly_edition"),
          entity("hub", "Comparison hub", "scholarly_edition"),
          entity("deep", "Underlying source"),
          ...leaves,
        ]}
        relations={[
          relation("hub", "collated_against", "edition", "hub", "Edition", "Comparison hub"),
          ...leaves.map((item, index) =>
            relation(
              `leaf-relation:${index}`,
              "collated_against",
              "edition",
              item.id,
              "Edition",
              item.label ?? item.id,
            ),
          ),
          relation("deep", "version_of", "hub", "deep", "Comparison hub", "Underlying source"),
        ]}
      />,
    );

    expect(screen.getByText("Comparison hub")).toBeInTheDocument();
    expect(screen.getByText("Underlying source")).toBeInTheDocument();
    expect(screen.getByText("12 relationships")).toBeInTheDocument();
    expect(screen.queryByText("Leaf 12")).not.toBeInTheDocument();
  });

  it("shows exact entity IDs when two diagram nodes share a human label", () => {
    render(
      <LineageDiagram
        title="Supporting relationships"
        entities={[
          entity("catalog", "Source catalog", "catalog_description"),
          entity("witness:one", "Accounts 1378-9"),
          entity("witness:two", "Accounts 1378-9"),
        ]}
        relations={[
          relation("one", "describes", "catalog", "witness:one", "Source catalog", "Accounts 1378-9"),
          relation("two", "describes", "catalog", "witness:two", "Source catalog", "Accounts 1378-9"),
        ]}
      />,
    );

    expect(screen.getByText("witness:one")).toBeInTheDocument();
    expect(screen.getByText("witness:two")).toBeInTheDocument();
  });
});
