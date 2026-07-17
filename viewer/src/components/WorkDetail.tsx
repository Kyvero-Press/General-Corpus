import { useEffect, useRef, useState } from "react";

import { assetUrl, publicationLink, safeExternalHttpUrl } from "../catalog";
import { humanizeToken } from "../filters";
import { duplicateEntityLabelIds, partitionLineageRelations } from "../lineage";
import { LineageDiagram } from "./LineageDiagram";
import type {
  AccessRecord,
  ContentPart,
  LineageEntity,
  LineageRelation,
  LineageRelationClassification,
  MetadataStatement,
  RightRecord,
  WorkDetailRecord,
  QuestionRecord,
} from "../types";

interface WorkDetailProps {
  detail: WorkDetailRecord | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

function ExternalLink({ href, children }: { href: string; children: React.ReactNode }) {
  const safeHref = safeExternalHttpUrl(href);
  if (!safeHref) return <span className="invalid-link">{children} (invalid URL)</span>;
  return (
    <a href={safeHref} target="_blank" rel="noopener noreferrer">
      {children} <span aria-hidden="true">↗</span>
    </a>
  );
}

function StatusBadge({ value }: { value: string | null | undefined }) {
  return <span className="mini-badge">{humanizeToken(value)}</span>;
}

function Notes({ notes }: { notes?: string[] }) {
  if (!notes?.length) return null;
  return (
    <ul className="compact-notes">
      {notes.map((note, index) => (
        <li key={`${index}:${note}`}>{note}</li>
      ))}
    </ul>
  );
}

function ResearchQuestions({ questions }: { questions: QuestionRecord[] }) {
  if (!questions.length) return null;
  return (
    <div className="research-questions">
      {questions.map((question, index) => (
        <article key={question.id ?? index}>
          <div className="research-question-heading">
            <strong>{question.question ?? "Open research question"}</strong>
            <div>
              {question.impact && <StatusBadge value={`${question.impact} impact`} />}
              {question.status && <StatusBadge value={question.status} />}
            </div>
          </div>
          {question.last_checked && <small>Last checked {question.last_checked}</small>}
          {question.next_steps && question.next_steps.length > 0 && (
            <>
              <h5>Suggested next steps</h5>
              <Notes notes={question.next_steps} />
            </>
          )}
          <Notes notes={question.notes} />
        </article>
      ))}
    </div>
  );
}

function RightsNotice({ right }: { right: RightRecord }) {
  return (
    <div className="rights-notice">
      <div className="rights-heading">
        <strong>{right.component ?? "Rights statement"}</strong>
        <StatusBadge value={right.copyright_status} />
      </div>
      <p className="rights-meta">
        {right.jurisdiction ?? "Jurisdiction not recorded"}
        {right.as_of ? ` · reviewed ${right.as_of}` : ""}
      </p>
      {right.basis && <p>{right.basis}</p>}
      {right.contract_terms_status && (
        <p>
          <strong>Provider terms:</strong> {humanizeToken(right.contract_terms_status)}
        </p>
      )}
      {right.effective_until && (
        <p>
          <strong>Re-review after:</strong> {right.effective_until}
        </p>
      )}
      {right.rights_statement_uri && (
        <p>
          <ExternalLink href={right.rights_statement_uri}>Rights statement</ExternalLink>
        </p>
      )}
      <Notes notes={right.notes} />
    </div>
  );
}

function accessActionLabel(access: AccessRecord): string {
  if (access.status === "no_public_copy_found") return "Review availability search";
  if (access.resourceKind === "catalog_record") return "View catalog record";
  if (access.resourceKind === "reproduction_order") return "Request reproduction";
  if (access.resourceKind === "physical_manuscript") return "Plan onsite access";
  if (access.resourceKind === "repository_enquiry") return "View enquiry instructions";
  if (access.resourceKind === "microfilm") return "Request microfilm access";
  if (access.resourceKind === "digital_text") return "Read digital text";
  if (access.resourceKind === "page_images") return "View page images";
  if (access.resourceKind === "download") return "Open source download";
  if (access.resourceKind === "repository_file") return "Open repository file";
  if (access.status === "requestable") return "Request access";
  return "Open access record";
}

function AccessCard({ access }: { access: AccessRecord }) {
  const availableCopies = access.localCopies.filter((copy) => copy.available).length;
  return (
    <article className="access-card">
      <div className="access-card-heading">
        <div>
          <p className="eyebrow">{humanizeToken(access.resourceKind)}</p>
          <h4>{access.provider ?? "Provider not recorded"}</h4>
        </div>
        <div className="access-statuses">
          <StatusBadge value={access.status} />
          {access.localCopies.length > 0 && (
            <StatusBadge
              value={
                availableCopies === access.localCopies.length
                  ? "downloaded locally"
                  : availableCopies > 0
                    ? "partly downloaded"
                    : "cache files absent"
              }
            />
          )}
        </div>
      </div>
      {access.accessMethod && <p>{access.accessMethod}</p>}
      <dl className="inline-facts">
        {access.format && (
          <div>
            <dt>Format</dt>
            <dd>{access.format}</dd>
          </div>
        )}
        {access.cost && (
          <div>
            <dt>Cost</dt>
            <dd>{humanizeToken(access.cost)}</dd>
          </div>
        )}
        {access.lastChecked && (
          <div>
            <dt>Checked</dt>
            <dd>{access.lastChecked}</dd>
          </div>
        )}
      </dl>
      {access.localCopies.map((localCopy) => (
        <div
          className={`local-copy ${localCopy.available ? "is-available" : "is-absent"}`}
          key={localCopy.path}
        >
          <strong>
            {localCopy.available
              ? `Checksum-verified local copy: ${localCopy.label}`
              : `Local copy recorded but absent: ${localCopy.label}`}
          </strong>
          <dl>
            <div>
              <dt>Cache path</dt>
              <dd><code>{localCopy.path}</code></dd>
            </div>
            <div>
              <dt>File</dt>
              <dd>{localCopy.sizeLabel ?? `${localCopy.bytes} bytes`} · {localCopy.mediaType}</dd>
            </div>
            <div>
              <dt>Source coverage</dt>
              <dd>{humanizeToken(localCopy.coverage)}</dd>
            </div>
            <div>
              <dt>Retrieval</dt>
              <dd>{humanizeToken(localCopy.retrievalMethod)}</dd>
            </div>
            {localCopy.sourceFileCount && (
              <div>
                <dt>Source files</dt>
                <dd>{localCopy.sourceFileCount.toLocaleString()}</dd>
              </div>
            )}
            {localCopy.bundleSourceKind && (
              <div>
                <dt>Bundle source</dt>
                <dd>{humanizeToken(localCopy.bundleSourceKind)}</dd>
              </div>
            )}
            <div>
              <dt>Downloaded</dt>
              <dd>{localCopy.downloadedOn}</dd>
            </div>
            <div>
              <dt>SHA-256</dt>
              <dd><code>{localCopy.sha256}</code></dd>
            </div>
          </dl>
          {localCopy.workPortion && (
            <div className="work-portion">
              <strong>Work location within source: {localCopy.workPortion.label}</strong>
              <ul className="compact-notes">
                {localCopy.workPortion.locators.map((locator) => (
                  <li key={locator}>{locator}</li>
                ))}
              </ul>
              {(localCopy.workPortion.startUrl || localCopy.workPortion.endUrl) && (
                <div className="work-portion-actions">
                  {localCopy.workPortion.startUrl && (
                    <ExternalLink href={localCopy.workPortion.startUrl}>Open work start</ExternalLink>
                  )}
                  {localCopy.workPortion.endUrl && (
                    <ExternalLink href={localCopy.workPortion.endUrl}>Open work end</ExternalLink>
                  )}
                </div>
              )}
              <Notes notes={localCopy.workPortion.notes} />
            </div>
          )}
          <div className="local-copy-action">
            <ExternalLink href={localCopy.sourceUrl}>
              {localCopy.retrievalMethod === "iiif_bundle"
                ? localCopy.bundleSourceKind === "image_url_inventory"
                  ? "Complete IIIF source record"
                  : "Exact IIIF manifest"
                : "Exact file download"}
            </ExternalLink>
          </div>
          <Notes notes={localCopy.notes} />
        </div>
      ))}
      <div className="access-actions">
        {access.url && (
          <ExternalLink href={access.url}>{accessActionLabel(access)}</ExternalLink>
        )}
        {access.alternateUrls.filter(
          (url) => !access.localCopies.some((copy) => copy.sourceUrl === url),
        ).map((url, index) => (
          <ExternalLink href={url} key={url}>
            Alternate link {index + 1}
          </ExternalLink>
        ))}
        {access.contact && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(access.contact) && (
          <a href={`mailto:${access.contact}`}>Email {access.contact}</a>
        )}
      </div>
      <Notes notes={access.notes} />
      {access.rights.length > 0 && (
        <div className="access-rights">
          <h5>Rights for this access copy</h5>
          {access.rights.map((right) => (
            <RightsNotice right={right} key={right.id ?? right.component} />
          ))}
        </div>
      )}
    </article>
  );
}

function EntityCard({ entity }: { entity: LineageEntity }) {
  const headingId = `source-heading-${encodeURIComponent(entity.id)}`;
  const generalRights = entity.rights.filter((right) => !right.access_id);
  const citation =
    typeof entity.bibliographic?.citation === "string"
      ? entity.bibliographic.citation
      : null;
  const shelfmark =
    typeof entity.holding?.shelfmark === "string" ? entity.holding.shelfmark : null;
  const historicalDesignations = Array.isArray(entity.holding?.historical_designations)
    ? entity.holding.historical_designations.filter(
        (value): value is string => typeof value === "string",
      )
    : [];
  const physicalFacts = ["support", "extent", "format"].flatMap((key) => {
    const value = entity.physicalDescription?.[key];
    return typeof value === "string" ? [{ key, value }] : [];
  });
  const physicalNotes = Array.isArray(entity.physicalDescription?.notes)
    ? entity.physicalDescription.notes.filter(
        (value): value is string => typeof value === "string",
      )
    : [];
  const holdingNotes =
    typeof entity.holding?.notes === "string" ? [entity.holding.notes] : [];
  return (
    <article
      className="entity-card"
      id={`source-${encodeURIComponent(entity.id)}`}
      aria-labelledby={headingId}
      tabIndex={-1}
    >
      <div className="entity-heading">
        <div>
          <p className="eyebrow">{humanizeToken(entity.type)}</p>
          <h3 id={headingId}>{entity.label ?? entity.id}</h3>
        </div>
        {entity.survivalStatus && <StatusBadge value={entity.survivalStatus} />}
      </div>
      {entity.description && <p>{entity.description}</p>}
      {citation && <p className="source-citation">{citation}</p>}
      {(shelfmark || historicalDesignations.length > 0 || entity.identifiers.length > 0) && (
        <dl className="source-identifiers">
          {shelfmark && (
            <div>
              <dt>Shelfmark</dt>
              <dd>{shelfmark}</dd>
            </div>
          )}
          {historicalDesignations.length > 0 && (
            <div>
              <dt>Historical designation</dt>
              <dd>{historicalDesignations.join("; ")}</dd>
            </div>
          )}
          {entity.identifiers.map((identifier, index) => {
            const scheme = typeof identifier.scheme === "string" ? identifier.scheme : "Identifier";
            const value = typeof identifier.value === "string" ? identifier.value : null;
            return value ? (
              <div key={`${scheme}:${value}:${index}`}>
                <dt>{scheme}</dt>
                <dd>{value}</dd>
              </div>
            ) : null;
          })}
        </dl>
      )}
      {physicalFacts.length > 0 && (
        <dl className="source-identifiers physical-description">
          {physicalFacts.map((fact) => (
            <div key={fact.key}>
              <dt>{humanizeToken(fact.key)}</dt>
              <dd>{fact.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {entity.dateStatements.length > 0 && (
        <div className="source-dates">
          <h4>Source dates</h4>
          <ul className="statement-list">
            {entity.dateStatements.map((statement, index) => (
              <li key={statement.id ?? index}>
                <span>
                  {statement.label ? `${statement.label}: ` : ""}
                  {statement.value ??
                    statement.display ??
                    String(statement.normalized ?? "Not recorded")}
                </span>
                {typeof statement.normalized === "string" &&
                  statement.normalized !== statement.value && (
                    <small>Normalized {statement.normalized}</small>
                  )}
              </li>
            ))}
          </ul>
        </div>
      )}
      <Notes notes={[...holdingNotes, ...physicalNotes]} />
      <Notes notes={entity.notes} />
      {entity.access.length > 0 ? (
        <div className="access-grid">
          {entity.access.map((access) => (
            <AccessCard access={access} key={access.id ?? `${entity.id}:${access.url}`} />
          ))}
        </div>
      ) : (
        <p className="empty-inline">No access route has been recorded for this source.</p>
      )}
      {generalRights.length > 0 && (
        <div className="entity-rights">
          <h4>Rights attached to this source</h4>
          <p className="section-caveat">
            These assessments apply only to the component and jurisdiction named in each statement.
          </p>
          {generalRights.map((right) => (
            <RightsNotice right={right} key={right.id ?? right.component} />
          ))}
        </div>
      )}
    </article>
  );
}

function statementText(statement: MetadataStatement): string {
  return (
    statement.display ??
    statement.placeLabel ??
    statement.description ??
    statement.label ??
    statement.value ??
    statement.term ??
    humanizeToken(statement.type)
  );
}

function StatementList({ statements }: { statements: MetadataStatement[] }) {
  if (!statements.length) return <p className="empty-inline">Not yet recorded.</p>;
  return (
    <ul className="statement-list">
      {statements.map((statement, index) => (
        <li key={statement.id ?? `${index}:${statementText(statement)}`}>
          <span>{statementText(statement)}</span>
          {(statement.type || statement.usage) && (
            <small>{humanizeToken(statement.usage ?? statement.type)}</small>
          )}
        </li>
      ))}
    </ul>
  );
}

function partDescription(part: ContentPart): string | null {
  return part.summary ?? part.description ?? part.scope?.description ?? null;
}

function RelationRecord({
  relation,
  duplicateLabelIds,
}: {
  relation: LineageRelation;
  duplicateLabelIds: ReadonlySet<string>;
}) {
  const subjectScope = relation.scope?.subject;
  const objectScope = relation.scope?.object;
  const locators = [
    ...(subjectScope?.locators ?? []).map((value) => `Source side: ${value}`),
    ...(objectScope?.locators ?? []).map((value) => `Earlier source: ${value}`),
  ];
  const hasDetails = Boolean(
    subjectScope || objectScope || relation.assertion || relation.scope?.notes,
  );
  const endpoint = (id: string | null, label: string | null) => (
    <>
      <span>{label ?? id}</span>
      {id && duplicateLabelIds.has(id) && <code className="relation-entity-id">{id}</code>}
    </>
  );
  return (
    <tbody className="relation-record">
      <tr className="relation-table-summary">
        <td data-label="From source">{endpoint(relation.subjectId, relation.subjectLabel)}</td>
        <th data-label="Relationship" scope="row">
          <span aria-hidden="true">→</span> {humanizeToken(relation.type)} <span aria-hidden="true">→</span>
        </th>
        <td data-label="To source">{endpoint(relation.objectId, relation.objectLabel)}</td>
      </tr>
      {hasDetails && (
        <tr className="relation-table-details-row">
          <td colSpan={3}>
            <div className="relation-details">
              <div className="relation-scope-copy">
                {subjectScope?.description && <p><strong>Derived material:</strong> {subjectScope.description}</p>}
                {objectScope?.description && <p><strong>Source material:</strong> {objectScope.description}</p>}
              </div>
              <div className="relation-certainty">
                {relation.assertion?.status && <StatusBadge value={relation.assertion.status} />}
                {relation.assertion?.confidence && (
                  <StatusBadge value={`${relation.assertion.confidence} confidence`} />
                )}
              </div>
              {locators.length > 0 && (
                <details>
                  <summary>Scope locators ({locators.length})</summary>
                  <Notes notes={locators} />
                </details>
              )}
              {relation.scope?.notes && <p className="relation-note">{relation.scope.notes}</p>}
              {relation.assertion?.notes && <p className="relation-note">{relation.assertion.notes}</p>}
            </div>
          </td>
        </tr>
      )}
    </tbody>
  );
}

function RelationGroup({
  title,
  description,
  relations,
  entities,
  view,
}: {
  title: string;
  description: string;
  relations: LineageRelation[];
  entities: LineageEntity[];
  view: "diagram" | "table";
}) {
  if (!relations.length) return null;
  const duplicateLabelIds = duplicateEntityLabelIds(entities);
  return (
    <div className="relation-group">
      <div className="relation-group-heading">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {view === "diagram" ? (
        <LineageDiagram title={title} entities={entities} relations={relations} />
      ) : (
        <div className="provenance-table-scroll">
          <table className="relation-table">
            <caption className="visually-hidden">{title}</caption>
            <thead>
              <tr>
                <th scope="col">From source</th>
                <th scope="col">Relationship</th>
                <th scope="col">To source</th>
              </tr>
            </thead>
            {relations.map((relation, index) => (
              <RelationRecord
                relation={relation}
                duplicateLabelIds={duplicateLabelIds}
                key={relation.id ?? index}
              />
            ))}
          </table>
        </div>
      )}
    </div>
  );
}

function ReviewedRelationshipClassification({
  classification,
}: {
  classification: LineageRelationClassification;
}) {
  const records = [
    ...classification.primaryTransmissionPaths.map((path) => ({
      id: path.id,
      label: path.label,
      description: path.description,
      count: path.relationIds.length,
      kind: "Primary path",
    })),
    ...classification.supportingRelationships.map((group) => ({
      id: group.id,
      label: group.label,
      description: group.description,
      count: group.relationIds.length,
      kind: "Supporting group",
    })),
  ];
  if (!records.length) return null;
  return (
    <div className="research-notes">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">Evidence-reviewed organization</p>
          <h3>Manifest path definitions</h3>
        </div>
        <StatusBadge value="explicit classification" />
      </div>
      <ul className="statement-list">
        {records.map((record) => (
          <li key={record.id}>
            <span>{record.label}</span>
            <small>
              {record.kind} · {record.count.toLocaleString()} {record.count === 1 ? "relationship" : "relationships"}
            </small>
            <p>{record.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MetadataSection({ detail }: { detail: WorkDetailRecord }) {
  const metadata = detail.metadata;
  if (!metadata) {
    return (
      <section className="detail-section" id="catalog-description">
        <p className="eyebrow">Catalog description</p>
        <h2>Metadata research is pending</h2>
        <p>
          This PDF belongs to the publication set, but a reviewed descriptive record has not yet been added.
          No date, region, or genre is inferred from its filename. Separately indexed source research appears below when available.
        </p>
      </section>
    );
  }
  return (
    <section className="detail-section" id="catalog-description">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">Catalog description</p>
          <h2>About this work</h2>
        </div>
        <StatusBadge value={metadata.recordStatus} />
      </div>
      <div className="metadata-columns">
        <div>
          <h3>Responsibilities</h3>
          <ul className="statement-list">
            {metadata.responsibilities.map((item, index) => (
              <li key={item.id ?? index}>
                <span>{item.agentName ?? item.display_name ?? "Anonymous"}</span>
                <small>
                  {humanizeToken(item.role)} · {humanizeToken(item.attribution_status)}
                </small>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Languages</h3>
          <StatementList statements={metadata.languageStatements} />
        </div>
        <div>
          <h3>Dates</h3>
          <StatementList statements={metadata.dateStatements} />
        </div>
        <div>
          <h3>Places and regions</h3>
          <StatementList statements={metadata.placeStatements} />
        </div>
        <div>
          <h3>Form</h3>
          <StatementList statements={metadata.formStatements} />
        </div>
        <div>
          <h3>Subjects</h3>
          <div className="tag-row">
            {metadata.subjects.map((subject, index) => (
              <span className="tag" key={subject.id ?? subject.term ?? index}>
                {subject.label ?? humanizeToken(subject.term)}
              </span>
            ))}
          </div>
        </div>
        <div>
          <h3>Genres</h3>
          <div className="tag-row">
            {metadata.genres.map((genre, index) => (
              <span className="tag" key={genre.id ?? genre.term ?? index}>
                {genre.label ?? humanizeToken(genre.term)}
              </span>
            ))}
          </div>
        </div>
        <div>
          <h3>Tags</h3>
          <div className="tag-row">
            {metadata.tags.map((tag) => (
              <span className="tag" key={tag}>{humanizeToken(tag)}</span>
            ))}
          </div>
        </div>
      </div>

      {metadata.contentParts.length > 0 && (
        <div className="contents-block">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">Encoded structure</p>
              <h3>Contents</h3>
            </div>
            <StatusBadge value={metadata.contentStructureStatus} />
          </div>
          <ol className="contents-list">
            {metadata.contentParts.map((part, index) => (
              <li key={part.id ?? index}>
                <span className="content-number">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{part.label ?? part.id ?? `Part ${index + 1}`}</strong>
                  {partDescription(part) && <p>{partDescription(part)}</p>}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
      {metadata.openQuestions.length > 0 && (
        <div className="research-notes">
          <h3>Cataloging questions</h3>
          <p>These remain open and are not silently resolved by the summary above.</p>
          <ResearchQuestions questions={metadata.openQuestions} />
        </div>
      )}
      <Notes notes={metadata.notes} />
    </section>
  );
}

function PublicationSection({ detail }: { detail: WorkDetailRecord }) {
  const [preview, setPreview] = useState(false);
  const publication = detail.work.publication;
  const link = publicationLink(publication);
  const previewId = `pdf-preview-${detail.work.workId}`;
  return (
    <section className="detail-section publication-section" id="publication-pdf">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">Ready for reading and print</p>
          <h2>Publication PDF</h2>
        </div>
        <StatusBadge value={publication.status} />
      </div>
      {link ? (
        <>
          <div className="pdf-action-row">
            <a
              className="button button-primary"
              href={link.url}
              download={link.isLocal ? publication.filename : undefined}
              target={link.isLocal ? undefined : "_blank"}
              rel={link.isLocal ? undefined : "noopener noreferrer"}
            >
              {link.isLocal ? "Download PDF" : "Open hosted PDF"}
            </a>
            <a
              className="button button-secondary"
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open in new tab
            </a>
            <button
              className="button button-secondary"
              type="button"
              aria-expanded={preview}
              aria-controls={previewId}
              onClick={() => setPreview((value) => !value)}
            >
              {preview ? "Hide preview" : "Preview here"}
            </button>
          </div>
          <dl className="pdf-facts">
            <div>
              <dt>File</dt>
              <dd>{publication.filename}</dd>
            </div>
            <div>
              <dt>Extent</dt>
              <dd>
                {publication.pages ? `${publication.pages} pages` : "Page count unavailable"}
                {publication.sizeLabel ? ` · ${publication.sizeLabel}` : ""}
              </dd>
            </div>
            {publication.pageSize && (
              <div>
                <dt>Page size</dt>
                <dd>{publication.pageSize}</dd>
              </div>
            )}
            {publication.sha256 && (
              <div>
                <dt>SHA-256</dt>
                <dd className="checksum" title={publication.sha256}>
                  {publication.sha256}
                </dd>
              </div>
            )}
          </dl>
          {preview && (
            <div className="pdf-preview" id={previewId}>
              <p>
                If this browser or an external host blocks the embedded preview, use “Open in new tab” above.
              </p>
              <iframe src={link.url} title={`PDF preview: ${detail.work.displayTitle}`} />
            </div>
          )}
        </>
      ) : (
        <div className="notice-box">
          <strong>PDF not available from this deployment.</strong>
          <p>
            The catalog record remains useful for source research, but this site has no staged or hosted PDF link.
          </p>
        </div>
      )}
    </section>
  );
}

function LineageSection({ detail }: { detail: WorkDetailRecord }) {
  const [relationshipView, setRelationshipView] = useState<"diagram" | "table">("diagram");
  const relationshipGroupsId = `lineage-relationship-groups-${detail.work.workId}`;
  const lineage = detail.lineage;
  if (!lineage) {
    return (
      <section className="detail-section" id="source-lineage">
        <p className="eyebrow">Source lineage</p>
        <h2>Source research has not yet been added</h2>
        <p>
          This record does not make a claim about which manuscript, edition, or digital transcription underlies the PDF.
        </p>
      </section>
    );
  }
  const partitionedRelations = partitionLineageRelations(
    lineage.entities,
    lineage.relations,
    lineage.primarySubjectId,
    lineage.relationClassification ?? null,
  );
  const hasReviewedClassification = Boolean(lineage.relationClassification);
  return (
    <section className="detail-section" id="source-lineage">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">Provenance and comparison</p>
          <h2>Source lineage</h2>
        </div>
        <StatusBadge value={lineage.recordStatus} />
      </div>
      {lineage.summary && <p className="lead-copy">{lineage.summary}</p>}
      {lineage.relationClassification && (
        <ReviewedRelationshipClassification
          classification={lineage.relationClassification}
        />
      )}
      {lineage.relations.length > 0 && (
        <div className="lineage-view-toolbar">
          <div>
            <p className="eyebrow">Relationship view</p>
            <p>
              The diagram emphasizes paths and branches. The table preserves the full scope,
              locators, certainty, and research notes for every relationship.
            </p>
          </div>
          <div className="lineage-view-switch" role="group" aria-label="Lineage relationship view">
            <button
              type="button"
              aria-pressed={relationshipView === "diagram"}
              aria-controls={relationshipGroupsId}
              onClick={() => setRelationshipView("diagram")}
            >
              Diagram
            </button>
            <button
              type="button"
              aria-pressed={relationshipView === "table"}
              aria-controls={relationshipGroupsId}
              onClick={() => setRelationshipView("table")}
            >
              Table
            </button>
          </div>
        </div>
      )}
      <div id={relationshipGroupsId}>
        <RelationGroup
          title="Primary transmission paths"
          description={hasReviewedClassification
            ? "Evidence-reviewed paths declared by the lineage manifest. Structurally necessary facsimile, containment, or version relationships retain their exact relation labels within the path."
            : "Direct copying, encoding, transcription, and excerpting relationships that can be followed from the repository artifact—or an encoding directly linked to it—toward its sources. Scope matters: separate sections may derive from different witnesses."}
          relations={partitionedRelations.primary}
          entities={lineage.entities}
          view={relationshipView}
        />
        <RelationGroup
          title="Other documented transmission paths"
          description={hasReviewedClassification
            ? "Relationships not included in the manifest's explicit classification. Valid reviewed manifests classify every relationship, so this defensive group should ordinarily be empty."
            : "Direct transcription or excerpting relationships recorded in this lineage but not connected to the repository artifact by a complete direct-edge chain. These often describe prior editions, comparison editions, or contextual textual ancestry."}
          relations={partitionedRelations.otherTransmission}
          entities={lineage.entities}
          view={relationshipView}
        />
        <RelationGroup
          title="Supporting relationships"
          description={hasReviewedClassification
            ? "Evidence-reviewed contextual and supporting groups declared by the lineage manifest. They remain visible without being presented as steps that produced the repository artifact."
            : "Collation, consultation, facsimile, catalog-description, and related scholarly connections. These do not automatically form the direct transmission path."}
          relations={partitionedRelations.supporting}
          entities={lineage.entities}
          view={relationshipView}
        />
      </div>

      <div className="sources-heading">
        <h3>Known sources and access routes</h3>
        <p>
          Links may lead to texts, scans, catalog records, onsite access, or reproduction requests. Rights notes remain attached to the exact source or access copy they describe.
        </p>
      </div>
      <div className="entity-list">
        {lineage.entities.map((entity) => (
          <EntityCard entity={entity} key={entity.id} />
        ))}
      </div>

      {(lineage.openQuestions.length > 0 || lineage.reviewNotes.length > 0) && (
        <div className="research-notes">
          <h3>Research status</h3>
          <ResearchQuestions questions={lineage.openQuestions} />
          <Notes notes={lineage.reviewNotes} />
        </div>
      )}
    </section>
  );
}

export function WorkDetail({ detail, loading, error, onClose }: WorkDetailProps) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const drawer = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    returnFocus.current = document.activeElement as HTMLElement | null;
    closeButton.current?.focus();
    const overlay = drawer.current?.parentElement;
    const background = overlay?.parentElement
      ? [...overlay.parentElement.children].filter(
          (element): element is HTMLElement =>
            element instanceof HTMLElement && element !== overlay,
        )
      : [];
    const backgroundState = background.map((element) => ({
      element,
      inert: element.inert,
      ariaHidden: element.getAttribute("aria-hidden"),
    }));
    for (const element of background) {
      element.inert = true;
      element.setAttribute("aria-hidden", "true");
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !drawer.current) return;
      const focusable = [...drawer.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])',
      )].filter((element) => !element.hasAttribute("hidden"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      for (const state of backgroundState) {
        state.element.inert = state.inert;
        if (state.ariaHidden === null) state.element.removeAttribute("aria-hidden");
        else state.element.setAttribute("aria-hidden", state.ariaHidden);
      }
      if (returnFocus.current?.isConnected) returnFocus.current.focus();
    };
  }, [onClose]);

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView?.({ block: "start" });
  };

  return (
    <div className="detail-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="detail-drawer" role="dialog" aria-modal="true" aria-label={detail?.work.displayTitle ?? "Work record"} ref={drawer}>
        <div className="detail-topbar">
          <span>General Corpus · work record</span>
          <button className="close-button" type="button" onClick={onClose} ref={closeButton}>
            Close <span aria-hidden="true">×</span>
          </button>
        </div>
        {loading && (
          <div className="detail-state" role="status">
            <span className="loading-mark" aria-hidden="true" />
            <h2>Opening the catalog record…</h2>
          </div>
        )}
        {error && (
          <div className="detail-state error-state" role="alert">
            <h2>The work record could not be loaded</h2>
            <p>{error}</p>
          </div>
        )}
        {detail && (
          <>
            <header className="detail-hero">
              <div>
                <p className="eyebrow">{detail.work.workId}</p>
                <h1>{detail.work.displayTitle}</h1>
                {detail.work.translatedTitle && detail.work.preferredTitle !== detail.work.displayTitle && (
                  <p className="detail-original-title">{detail.work.preferredTitle}</p>
                )}
                <p className="detail-byline">
                  {detail.work.author}
                  {detail.work.editor ? ` · edited by ${detail.work.editor}` : ""}
                </p>
              </div>
              <div className="detail-status-stack">
                <StatusBadge value={detail.work.metadataStatus} />
                <StatusBadge value={detail.work.lineageStatus === "available" ? "lineage linked" : "lineage pending"} />
              </div>
            </header>
            <nav className="detail-nav" aria-label="Work record sections">
              <button type="button" onClick={() => scrollToSection("publication-pdf")}>PDF</button>
              <button type="button" onClick={() => scrollToSection("catalog-description")}>Description</button>
              <button type="button" onClick={() => scrollToSection("source-lineage")}>Sources</button>
            </nav>
            <div className="detail-body">
              <section className="detail-section overview-section">
                <p className="eyebrow">Overview</p>
                <p className="detail-summary">{detail.work.summary}</p>
                {detail.work.metadataStatus === "cataloged" && (
                  <dl className="overview-facts">
                    <div>
                      <dt>Date</dt>
                      <dd>{detail.work.dateDisplay}</dd>
                    </div>
                    <div>
                      <dt>Region</dt>
                      <dd>{detail.work.regionDisplay}</dd>
                    </div>
                    <div>
                      <dt>Languages</dt>
                      <dd>{detail.work.languages.map((item) => item.label).join(", ")}</dd>
                    </div>
                    <div>
                      <dt>Form</dt>
                      <dd>{humanizeToken(detail.work.form)}</dd>
                    </div>
                  </dl>
                )}
              </section>
              <PublicationSection detail={detail} />
              <MetadataSection detail={detail} />
              <LineageSection detail={detail} />
              {(detail.metadataManifestPath || detail.lineageManifestPath) && (
                <section className="detail-section raw-records">
                  <p className="eyebrow">For researchers and maintainers</p>
                  <h2>Raw manifest records</h2>
                  <p>Inspect the complete structured assertions, evidence bindings, and review notes used to build this page.</p>
                  <div className="raw-links">
                    {detail.metadataManifestPath && (
                      <a href={assetUrl(detail.metadataManifestPath)}>Descriptive metadata JSON</a>
                    )}
                    {detail.lineageManifestPath && (
                      <a href={assetUrl(detail.lineageManifestPath)}>Source lineage JSON</a>
                    )}
                  </div>
                </section>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
