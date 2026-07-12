import { useId, useState } from "react";

import { humanizeToken } from "../filters";
import { buildLineageForest, duplicateEntityLabelIds } from "../lineage";
import type { DiagramBranch, DiagramNode } from "../lineage";
import type { LineageEntity, LineageRelation } from "../types";

interface LineageDiagramProps {
  title: string;
  entities: LineageEntity[];
  relations: LineageRelation[];
}

const LARGE_BRANCH_SET = 12;
const COLLAPSIBLE_RELATION_GROUP = 6;

function relationLabel(type: string | null): string {
  return humanizeToken(type ?? "related to");
}

function entityCategory(type: string | null): string {
  if (!type) return "other";
  if (type === "repository_artifact") return "artifact";
  if (type === "digital_encoding") return "encoding";
  if (type === "manuscript_witness") return "witness";
  if (type === "facsimile") return "facsimile";
  if (type.includes("edition") || type === "transcript") return "edition";
  if (type.includes("catalog") || type === "bibliographic_record") return "reference";
  if (type.startsWith("work") || type.includes("source_work")) return "work";
  return "other";
}

function SourceNode({ node }: { node: DiagramNode }) {
  const anchorId = `source-${encodeURIComponent(node.id)}`;
  const stateDescription = node.cycle
    ? "Cycle returns to this source."
    : node.reference
      ? "Shared source; shown on another branch."
      : "";
  const accessibleLabel = [
    `View source details: ${node.label}.`,
    `${humanizeToken(node.type ?? "source")}.`,
    node.disambiguator ? `Identifier ${node.disambiguator}.` : "",
    stateDescription,
  ]
    .filter(Boolean)
    .join(" ");
  const content = (
    <>
      <span className="lineage-node-type">{humanizeToken(node.type ?? "source")}</span>
      <strong>{node.label}</strong>
      {node.disambiguator && <code className="lineage-node-id">{node.disambiguator}</code>}
      {node.cycle && <small>Cycle returns to this source</small>}
      {node.reference && <small>Shared source · shown on another branch</small>}
    </>
  );
  const className = `lineage-node lineage-node-${entityCategory(node.type)}`;

  if (!node.hasEntityRecord) return <div className={className}>{content}</div>;
  return (
    <a
      className={className}
      href={`#${anchorId}`}
      aria-label={accessibleLabel}
      onClick={(event) => {
        const target = document.getElementById(anchorId);
        if (!target) return;
        event.preventDefault();
        target.focus({ preventScroll: true });
        target.scrollIntoView({ block: "start" });
      }}
    >
      {content}
    </a>
  );
}

function RelationEdge({
  relation,
  grouped = false,
  relationshipCount = 1,
  mixedCertainty = false,
}: {
  relation: LineageRelation;
  grouped?: boolean;
  relationshipCount?: number;
  mixedCertainty?: boolean;
}) {
  return (
    <div className={`lineage-edge${grouped ? " lineage-edge-grouped" : ""}`}>
      <span aria-hidden="true">↓</span>
      <strong>{relationLabel(relation.type)}</strong>
      {!mixedCertainty && relation.assertion?.status && (
        <small>{humanizeToken(relation.assertion.status)}</small>
      )}
      {!mixedCertainty && relation.assertion?.confidence && (
        <small>{humanizeToken(relation.assertion.confidence)} confidence</small>
      )}
      {mixedCertainty && <small>Mixed certainty</small>}
      {relationshipCount > 1 && <small>{relationshipCount} scoped relationships</small>}
    </div>
  );
}

function TreeBranch({
  branch,
  grouped = false,
  relationshipCount = 1,
  mixedCertainty = false,
}: {
  branch: DiagramBranch;
  grouped?: boolean;
  relationshipCount?: number;
  mixedCertainty?: boolean;
}) {
  return (
    <li className="lineage-tree-branch" role="listitem">
      <RelationEdge
        relation={branch.relation}
        grouped={grouped}
        relationshipCount={relationshipCount}
        mixedCertainty={mixedCertainty}
      />
      <TreeNodeContent node={branch.target} />
    </li>
  );
}

interface CompactedScopedBranch {
  branch: DiagramBranch;
  count: number;
  mixedCertainty: boolean;
}

function compactScopedBranches(
  branches: DiagramBranch[],
): CompactedScopedBranch[] {
  const grouped = new Map<
    string,
    { branch: DiagramBranch; count: number; certaintySignatures: Set<string> }
  >();
  for (const branch of branches) {
    const key = `${branch.relation.type ?? "related_to"}\u0000${branch.target.id}`;
    const certaintySignature = [
      branch.relation.assertion?.status ?? "",
      branch.relation.assertion?.confidence ?? "",
    ].join("\u0000");
    const existing = grouped.get(key);
    if (existing) {
      existing.count += 1;
      existing.certaintySignatures.add(certaintySignature);
    } else {
      grouped.set(key, {
        branch,
        count: 1,
        certaintySignatures: new Set([certaintySignature]),
      });
    }
  }
  return [...grouped.values()].map(({ branch, count, certaintySignatures }) => ({
    branch,
    count,
    mixedCertainty: certaintySignatures.size > 1,
  }));
}

function LazyBranchGroup({
  type,
  branches,
}: {
  type: string;
  branches: CompactedScopedBranch[];
}) {
  const [open, setOpen] = useState(false);
  const relationshipCount = branches.reduce((total, item) => total + item.count, 0);
  return (
    <li className="lineage-tree-cluster" role="listitem">
      <details onToggle={(event) => setOpen(event.currentTarget.open)}>
        <summary>
          <span className="lineage-cluster-arrow" aria-hidden="true">↓</span>
          <strong>{relationLabel(type)}</strong>
          <span>{relationshipCount.toLocaleString()} relationships</span>
        </summary>
        {open && (
          <ol className="lineage-cluster-list" role="list">
            {branches.map(({ branch, count, mixedCertainty }) => (
              <TreeBranch
                branch={branch}
                grouped
                relationshipCount={count}
                mixedCertainty={mixedCertainty}
                key={branch.key}
              />
            ))}
          </ol>
        )}
      </details>
    </li>
  );
}

function BranchList({ branches }: { branches: DiagramBranch[] }) {
  if (!branches.length) return null;

  const groups = new Map<string, DiagramBranch[]>();
  for (const branch of branches) {
    const key = branch.relation.type ?? "related_to";
    const group = groups.get(key) ?? [];
    group.push(branch);
    groups.set(key, group);
  }
  const collapseLargeGroups = branches.length > LARGE_BRANCH_SET;

  return (
    <ol className="lineage-tree-children" role="list">
      {[...groups.entries()].flatMap(([type, group]) => {
        const compacted = compactScopedBranches(group);
        if (collapseLargeGroups && group.length >= COLLAPSIBLE_RELATION_GROUP) {
          const structural = compacted.filter((item) => item.branch.target.branches.length > 0);
          const leaves = compacted.filter((item) => item.branch.target.branches.length === 0);
          const leafRelationshipCount = leaves.reduce((total, item) => total + item.count, 0);
          const renderedStructural = structural.map(
            ({ branch, count, mixedCertainty }) => (
              <TreeBranch
                branch={branch}
                relationshipCount={count}
                mixedCertainty={mixedCertainty}
                key={branch.key}
              />
            ),
          );
          if (leafRelationshipCount >= COLLAPSIBLE_RELATION_GROUP) {
            return [
              ...renderedStructural,
              <LazyBranchGroup type={type} branches={leaves} key={`group:${type}`} />,
            ];
          }
          return [
            ...renderedStructural,
            ...leaves.map(({ branch, count, mixedCertainty }) => (
              <TreeBranch
                branch={branch}
                relationshipCount={count}
                mixedCertainty={mixedCertainty}
                key={branch.key}
              />
            )),
          ];
        }
        return compacted.map(({ branch, count, mixedCertainty }) => (
          <TreeBranch
            branch={branch}
            relationshipCount={count}
            mixedCertainty={mixedCertainty}
            key={branch.key}
          />
        ));
      })}
    </ol>
  );
}

function TreeNodeContent({ node }: { node: DiagramNode }) {
  return (
    <>
      <SourceNode node={node} />
      <BranchList branches={node.branches} />
    </>
  );
}

export function LineageDiagram({ title, entities, relations }: LineageDiagramProps) {
  const headingId = useId();
  const forest = buildLineageForest(entities, relations);
  if (!forest.relationCount) return null;
  const relationshipLabel = forest.relationCount === 1 ? "relationship" : "relationships";

  return (
    <figure className="lineage-diagram" aria-labelledby={headingId}>
      <figcaption>
        <div>
          <span className="eyebrow">Relationship diagram</span>
          <strong id={headingId}>{title}</strong>
        </div>
        <p>
          {forest.nodeCount.toLocaleString()} source records · {forest.relationCount.toLocaleString()} {relationshipLabel}.
          Direction follows each recorded subject-to-object relationship; select a source to jump to its full record.
        </p>
      </figcaption>
      {forest.omittedRelationCount > 0 && (
        <p className="lineage-diagram-warning">
          {forest.omittedRelationCount.toLocaleString()} malformed relationships could not be diagrammed;
          switch to Table view for their detailed records.
        </p>
      )}
      <ol className="lineage-tree-roots" role="list">
        {forest.roots.map((root) => (
          <li className="lineage-tree-root" key={root.id} role="listitem">
            <TreeNodeContent node={root} />
          </li>
        ))}
      </ol>
    </figure>
  );
}
