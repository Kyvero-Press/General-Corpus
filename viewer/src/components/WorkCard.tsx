import { publicationLink } from "../catalog";
import { humanizeToken } from "../filters";
import type { WorkCardRecord } from "../types";

interface WorkCardProps {
  work: WorkCardRecord;
  onOpen: (workId: string) => void;
}

export function WorkCard({ work, onOpen }: WorkCardProps) {
  const publication = publicationLink(work.publication);
  const cataloged = work.metadataStatus === "cataloged";
  return (
    <article className={`work-card ${cataloged ? "work-card-cataloged" : ""}`}>
      <div className="work-card-topline">
        <div className="work-card-badges">
          <span className={`status-badge ${cataloged ? "status-reviewed" : "status-pending"}`}>
            {cataloged ? "Catalog record" : "Metadata pending"}
          </span>
          {work.lineageStatus === "available" && (
            <span className="status-badge status-lineage">Sources linked</span>
          )}
        </div>
        <span className="work-id">{work.workId}</span>
      </div>

      <button className="work-title-button" type="button" onClick={() => onOpen(work.workId)}>
        <span className="work-card-title">{work.displayTitle}</span>
      </button>
      {work.translatedTitle && work.preferredTitle !== work.displayTitle && (
        <p className="original-title">
          {work.preferredTitle}
        </p>
      )}

      <p className="work-author">
        {work.author}
        {work.editor && <span> · Edited by {work.editor}</span>}
      </p>

      {cataloged ? (
        <>
          <p className="work-summary">{work.summary}</p>
          <dl className="work-facts">
            <div>
              <dt>Date</dt>
              <dd>{work.dateDisplay}</dd>
            </div>
            <div>
              <dt>Form</dt>
              <dd>{humanizeToken(work.form)}</dd>
            </div>
          </dl>
          <div className="tag-row" aria-label="Genres">
            {work.genres.slice(0, 4).map((genre) => (
              <span className="tag" key={genre.term}>
                {genre.label}
              </span>
            ))}
          </div>
        </>
      ) : (
        <p className="work-summary pending-summary">
          {work.lineageStatus === "available"
            ? "A printable corpus edition awaiting descriptive metadata; separately researched source lineage is available."
            : "A printable corpus edition. Scholarly description and source lineage have not yet been cataloged."}
        </p>
      )}

      <div className="work-card-footer">
        <button className="button button-secondary" type="button" onClick={() => onOpen(work.workId)}>
          View record
        </button>
        {publication ? (
          <a
            className="button button-quiet"
            href={publication.url}
            download={publication.isLocal ? work.publication.filename : undefined}
            target={publication.isLocal ? undefined : "_blank"}
            rel={publication.isLocal ? undefined : "noopener noreferrer"}
          >
            Download PDF
          </a>
        ) : (
          <span className="pdf-unavailable">PDF not staged</span>
        )}
      </div>
      <div className="publication-furniture" aria-hidden="true">
        <span>{work.publication.pages ? `${work.publication.pages} pages` : "PDF edition"}</span>
        <span>{work.publication.sizeLabel ?? ""}</span>
      </div>
    </article>
  );
}
