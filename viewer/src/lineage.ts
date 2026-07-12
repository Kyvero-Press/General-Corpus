import type { LineageEntity, LineageRelation } from "./types";

export const PRIMARY_TRANSMISSION_TYPES = new Set([
  "copied_from",
  "encoded_from",
  "excerpted_from",
  "transcribes",
]);

export function isPrimaryTransmissionRelation(relation: LineageRelation): boolean {
  return relation.type ? PRIMARY_TRANSMISSION_TYPES.has(relation.type) : false;
}

export interface PartitionedLineageRelations {
  primary: LineageRelation[];
  otherTransmission: LineageRelation[];
  supporting: LineageRelation[];
}

/**
 * Reserve "primary" for direct transmission edges that can actually be
 * followed from the corpus repository artifact. Direct edges in disconnected
 * components remain visible, but are not presented as if they produced the
 * corpus file. Older records without an artifact entity retain the legacy
 * direct/supporting split.
 */
export function partitionLineageRelations(
  entities: LineageEntity[],
  relations: LineageRelation[],
  primarySubjectId: string | null = null,
): PartitionedLineageRelations {
  const direct = relations.filter(isPrimaryTransmissionRelation);
  const supporting = relations.filter(
    (relation) => !isPrimaryTransmissionRelation(relation),
  );
  const repositoryArtifacts = entities.filter(
    (entity) => entity.type === "repository_artifact",
  );
  const conventionalCorpusArtifacts = repositoryArtifacts.filter((entity) =>
    entity.id.startsWith("artifact:general-corpus:"),
  );
  const artifactIds = new Set(
    primarySubjectId
      ? [primarySubjectId]
      : (conventionalCorpusArtifacts.length ? conventionalCorpusArtifacts : repositoryArtifacts)
          .map((entity) => entity.id),
  );
  if (!artifactIds.size) {
    return { primary: direct, otherTransmission: [], supporting };
  }

  const entityTypes = new Map(entities.map((entity) => [entity.id, entity.type]));
  // Some carefully qualified records use version_of, rather than a directional
  // copying claim, between the repository artifact and its U-M encoding. The
  // edge stays supporting, but the directly linked encoding is still the
  // correct place from which to follow proven downstream derivation edges.
  const traversalSeeds = new Set(artifactIds);
  for (const relation of relations) {
    if (
      relation.type === "version_of" &&
      relation.subjectId &&
      artifactIds.has(relation.subjectId) &&
      relation.objectId &&
      entityTypes.get(relation.objectId) === "digital_encoding"
    ) {
      traversalSeeds.add(relation.objectId);
    }
  }

  const outgoing = new Map<string, LineageRelation[]>();
  for (const relation of direct) {
    if (!relation.subjectId) continue;
    const subjectRelations = outgoing.get(relation.subjectId) ?? [];
    subjectRelations.push(relation);
    outgoing.set(relation.subjectId, subjectRelations);
  }
  const reachedEntities = new Set(traversalSeeds);
  const reachedRelations = new Set<LineageRelation>();
  const queue = [...traversalSeeds];
  for (let index = 0; index < queue.length; index += 1) {
    for (const relation of outgoing.get(queue[index]) ?? []) {
      reachedRelations.add(relation);
      if (relation.objectId && !reachedEntities.has(relation.objectId)) {
        reachedEntities.add(relation.objectId);
        queue.push(relation.objectId);
      }
    }
  }
  return {
    primary: direct.filter((relation) => reachedRelations.has(relation)),
    otherTransmission: direct.filter((relation) => !reachedRelations.has(relation)),
    supporting,
  };
}

interface DiagramNodeDescriptor {
  id: string;
  label: string;
  type: string | null;
  hasEntityRecord: boolean;
  disambiguator: string | null;
}

export interface DiagramBranch {
  key: string;
  relation: LineageRelation;
  target: DiagramNode;
}

export interface DiagramNode extends DiagramNodeDescriptor {
  branches: DiagramBranch[];
  cycle: boolean;
  reference: boolean;
}

export interface DiagramForest {
  roots: DiagramNode[];
  nodeCount: number;
  relationCount: number;
  omittedRelationCount: number;
}

interface IndexedRelation {
  key: string;
  relation: LineageRelation;
  subjectId: string;
  objectId: string;
}

export function duplicateEntityLabelIds(entities: LineageEntity[]): Set<string> {
  const counts = new Map<string, number>();
  for (const entity of entities) {
    const label = entity.label ?? entity.id;
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return new Set(
    entities
      .filter((entity) => (counts.get(entity.label ?? entity.id) ?? 0) > 1)
      .map((entity) => entity.id),
  );
}

/**
 * Convert a directed relation graph into a stable, readable forest. A source
 * shared by two branches is expanded at its first occurrence and shown as a
 * cross-reference thereafter. Cycles are marked and never recursively opened.
 */
export function buildLineageForest(
  entities: LineageEntity[],
  relations: LineageRelation[],
): DiagramForest {
  const descriptors = new Map<string, DiagramNodeDescriptor>();
  const duplicatedLabelIds = duplicateEntityLabelIds(entities);
  for (const entity of entities) {
    descriptors.set(entity.id, {
      id: entity.id,
      label: entity.label ?? entity.id,
      type: entity.type,
      hasEntityRecord: true,
      disambiguator: duplicatedLabelIds.has(entity.id) ? entity.id : null,
    });
  }

  const ensureDescriptor = (
    id: string,
    label: string | null,
  ): DiagramNodeDescriptor => {
    const existing = descriptors.get(id);
    if (existing) return existing;
    const descriptor = {
      id,
      label: label ?? id,
      type: null,
      hasEntityRecord: false,
      disambiguator: null,
    };
    descriptors.set(id, descriptor);
    return descriptor;
  };

  const indexed: IndexedRelation[] = [];
  const relationNodeIds = new Set<string>();
  const subjectOrder: string[] = [];
  const seenSubjects = new Set<string>();
  const objectIds = new Set<string>();
  const outgoing = new Map<string, IndexedRelation[]>();

  relations.forEach((relation, index) => {
    if (!relation.subjectId || !relation.objectId) return;
    ensureDescriptor(relation.subjectId, relation.subjectLabel);
    ensureDescriptor(relation.objectId, relation.objectLabel);
    const item = {
      key: relation.id ?? `${index}:${relation.subjectId}:${relation.objectId}`,
      relation,
      subjectId: relation.subjectId,
      objectId: relation.objectId,
    };
    indexed.push(item);
    relationNodeIds.add(item.subjectId);
    relationNodeIds.add(item.objectId);
    if (!seenSubjects.has(item.subjectId)) {
      subjectOrder.push(item.subjectId);
      seenSubjects.add(item.subjectId);
    }
    objectIds.add(item.objectId);
    const subjectRelations = outgoing.get(item.subjectId) ?? [];
    subjectRelations.push(item);
    outgoing.set(item.subjectId, subjectRelations);
  });

  const expanded = new Set<string>();
  const makeNode = (id: string, ancestry: ReadonlySet<string>): DiagramNode => {
    const descriptor = ensureDescriptor(id, null);
    if (ancestry.has(id)) {
      return { ...descriptor, branches: [], cycle: true, reference: false };
    }
    if (expanded.has(id)) {
      return { ...descriptor, branches: [], cycle: false, reference: true };
    }
    expanded.add(id);
    const nextAncestry = new Set(ancestry);
    nextAncestry.add(id);
    return {
      ...descriptor,
      cycle: false,
      reference: false,
      branches: (outgoing.get(id) ?? []).map((item) => ({
        key: item.key,
        relation: item.relation,
        target: makeNode(item.objectId, nextAncestry),
      })),
    };
  };

  const roots: DiagramNode[] = [];
  for (const id of subjectOrder.filter((subjectId) => !objectIds.has(subjectId))) {
    if (!expanded.has(id)) roots.push(makeNode(id, new Set()));
  }
  // A malformed or cyclic component has no ordinary root. Retaining it here
  // makes the diagram total over every valid relation instead of silently
  // dropping that component.
  for (const id of subjectOrder) {
    if (!expanded.has(id)) roots.push(makeNode(id, new Set()));
  }

  return {
    roots,
    nodeCount: relationNodeIds.size,
    relationCount: indexed.length,
    omittedRelationCount: relations.length - indexed.length,
  };
}
