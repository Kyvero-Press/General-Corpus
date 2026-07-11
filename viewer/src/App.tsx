import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { assetUrl, loadCatalog, loadWorkDetail } from "./catalog";
import { ActiveFilters, FilterPanel } from "./components/FilterPanel";
import { WorkCard } from "./components/WorkCard";
import { WorkDetail } from "./components/WorkDetail";
import {
  emptyFilters,
  filterAndSortWorks,
  parseFilters,
  selectedFilterCount,
  serializeFilters,
  type FilterState,
  type SortValue,
} from "./filters";
import type { CatalogIndex, WorkDetailRecord } from "./types";

function currentFilters(): FilterState {
  return parseFilters(new URLSearchParams(window.location.search));
}

function currentWorkId(): string | null {
  const hash = window.location.hash.replace(/^#/, "");
  if (!hash.startsWith("work=")) return null;
  try {
    // Unlike query strings, a literal + in a URL fragment is a valid path-like
    // identifier character and must not be decoded as a space.
    return decodeURIComponent(hash.slice("work=".length));
  } catch {
    return null;
  }
}

function writeFilters(filters: FilterState): void {
  const url = new URL(window.location.href);
  const query = serializeFilters(filters).toString();
  url.search = query ? `?${query}` : "";
  window.history.replaceState(window.history.state, "", url);
}

function humanBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`;
  const units = ["KiB", "MiB", "GiB"];
  let amount = bytes / 1024;
  let unit = units[0];
  for (let index = 1; index < units.length && amount >= 1024; index += 1) {
    amount /= 1024;
    unit = units[index];
  }
  return `${amount >= 100 ? amount.toFixed(0) : amount.toFixed(1)} ${unit}`;
}

function LoadingCatalog() {
  return (
    <main className="catalog-state" role="status">
      <span className="loading-mark" aria-hidden="true" />
      <p className="eyebrow">Preparing the shelves</p>
      <h1>Loading the General Corpus catalog…</h1>
    </main>
  );
}

function CatalogError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <main className="catalog-state error-state" role="alert">
      <p className="eyebrow">Catalog unavailable</p>
      <h1>The reader’s catalog could not be opened.</h1>
      <p>{message}</p>
      <button className="button button-primary" type="button" onClick={onRetry}>
        Try again
      </button>
    </main>
  );
}

export default function App() {
  const [catalog, setCatalog] = useState<CatalogIndex | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [filters, setFilters] = useState<FilterState>(currentFilters);
  const [mobileFilters, setMobileFilters] = useState(false);
  const [selectedWorkId, setSelectedWorkId] = useState<string | null>(currentWorkId);
  const [detail, setDetail] = useState<WorkDetailRecord | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const mobileFilterTrigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    setCatalogError(null);
    loadCatalog(controller.signal)
      .then(setCatalog)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setCatalogError(error instanceof Error ? error.message : "Unknown catalog error");
        }
      });
    return () => controller.abort();
  }, [catalogAttempt]);

  useEffect(() => {
    const syncLocation = () => {
      setFilters(currentFilters());
      setSelectedWorkId(currentWorkId());
    };
    window.addEventListener("popstate", syncLocation);
    window.addEventListener("hashchange", syncLocation);
    return () => {
      window.removeEventListener("popstate", syncLocation);
      window.removeEventListener("hashchange", syncLocation);
    };
  }, []);

  useEffect(() => {
    if (!mobileFilters) return;
    const previousFocus = mobileFilterTrigger.current;
    const previousOverflow = document.body.style.overflow;
    const overlay = document.querySelector<HTMLElement>(".mobile-filter-overlay");
    const panel = overlay?.querySelector<HTMLElement>(".filter-panel-mobile");
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
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileFilters(false);
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const focusable = [...panel.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
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
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = previousOverflow;
      for (const state of backgroundState) {
        state.element.inert = state.inert;
        if (state.ariaHidden === null) state.element.removeAttribute("aria-hidden");
        else state.element.setAttribute("aria-hidden", state.ariaHidden);
      }
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [mobileFilters]);

  const changeFilters = useCallback((next: FilterState) => {
    setFilters(next);
    writeFilters(next);
  }, []);

  const clearFilters = useCallback(() => {
    const next = { ...emptyFilters, sort: filters.sort };
    setFilters(next);
    writeFilters(next);
  }, [filters.sort]);

  const openWork = useCallback((workId: string) => {
    const url = new URL(window.location.href);
    url.hash = new URLSearchParams({ work: workId }).toString();
    window.history.pushState({ workId }, "", url);
    setSelectedWorkId(workId);
  }, []);

  const closeWork = useCallback(() => {
    const url = new URL(window.location.href);
    url.hash = "";
    window.history.replaceState(window.history.state, "", url);
    setSelectedWorkId(null);
    setDetail(null);
    setDetailError(null);
  }, []);

  useEffect(() => {
    if (!selectedWorkId || !catalog) {
      setDetail(null);
      setDetailLoading(false);
      return;
    }
    const card = catalog.works.find((work) => work.workId === selectedWorkId);
    if (!card) {
      setDetail(null);
      setDetailLoading(false);
      setDetailError(`No catalog work has the identifier “${selectedWorkId}”.`);
      return;
    }
    const controller = new AbortController();
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    loadWorkDetail(card.detailPath, controller.signal)
      .then((record) => {
        setDetail(record);
        setDetailLoading(false);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setDetailError(error instanceof Error ? error.message : "Unknown work-record error");
          setDetailLoading(false);
        }
      });
    return () => controller.abort();
  }, [catalog, selectedWorkId]);

  const works = useMemo(
    () => (catalog ? filterAndSortWorks(catalog.works, filters) : []),
    [catalog, filters],
  );
  const activeCount = selectedFilterCount(filters);

  if (catalogError && !catalog) {
    return <CatalogError message={catalogError} onRetry={() => setCatalogAttempt((value) => value + 1)} />;
  }
  if (!catalog) return <LoadingCatalog />;

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="masthead">
          <a className="press-mark" href="./" aria-label="General Corpus catalog home">
            <span className="press-monogram" aria-hidden="true">GC</span>
            <span>
              <strong>General Corpus</strong>
              <small>Reader’s catalog</small>
            </span>
          </a>
        </div>
        <div className="hero">
          <dl className="catalog-totals" aria-label="Catalog totals">
            <div>
              <dt>{catalog.counts.works.toLocaleString()}</dt>
              <dd>editions listed</dd>
            </div>
            <div>
              <dt>{catalog.counts.pdfsAvailable.toLocaleString()}</dt>
              <dd>PDFs available</dd>
            </div>
            <div>
              <dt>{catalog.counts.lineageRecords.toLocaleString()}</dt>
              <dd>source records</dd>
            </div>
            <div>
              <dt>{humanBytes(catalog.counts.publicationBytes)}</dt>
              <dd>publication set</dd>
            </div>
          </dl>
        </div>
      </header>

      <main className="catalog-main">
        <div className="catalog-intro">
          <div>
            <p className="eyebrow">The catalog</p>
            <h2>Find an edition</h2>
          </div>
          <p>
            Descriptive coverage is incremental. Records marked <strong>metadata pending</strong> are printable editions whose dates and genres have not yet been reviewed; a separately researched source lineage may still be available.
          </p>
        </div>

        <div className="toolbar">
          <label className="search-field">
            <span className="visually-hidden">Search works</span>
            <span className="search-icon" aria-hidden="true">⌕</span>
            <input
              type="search"
              value={filters.query}
              placeholder="Search title, author, language, genre, or ID…"
              onChange={(event) => changeFilters({ ...filters, query: event.target.value })}
            />
          </label>
          <label className="sort-field">
            <span>Sort</span>
            <select
              value={filters.sort}
              onChange={(event) =>
                changeFilters({ ...filters, sort: event.target.value as SortValue })
              }
            >
              <option value="catalog-order">Catalog order</option>
              <option value="title">Title A–Z</option>
              <option value="author">Author A–Z</option>
              <option value="publication-oldest">Edition date, oldest</option>
              <option value="publication-newest">Edition date, newest</option>
            </select>
          </label>
          <button className="button button-secondary mobile-filter-button" type="button" onClick={() => setMobileFilters(true)} ref={mobileFilterTrigger}>
            Filters{activeCount ? ` (${activeCount})` : ""}
          </button>
        </div>

        <ActiveFilters catalog={catalog} filters={filters} onChange={changeFilters} onClear={clearFilters} />

        <div className="catalog-layout">
          <aside className="desktop-filters" aria-label="Catalog filters">
            <FilterPanel
              catalog={catalog}
              filters={filters}
              onChange={changeFilters}
              onClear={clearFilters}
            />
          </aside>
          <section className="catalog-results" id="catalog-results" aria-labelledby="results-heading">
            <div className="results-heading">
              <div>
                <p className="eyebrow">Showing the shelves</p>
                <h2 id="results-heading" role="status" aria-live="polite" aria-atomic="true">
                  {works.length.toLocaleString()} {works.length === 1 ? "work" : "works"}
                </h2>
              </div>
              <p aria-live="polite">
                {works.length === catalog.works.length
                  ? "All catalog entries"
                  : `Filtered from ${catalog.works.length.toLocaleString()}`}
              </p>
            </div>
            {works.length > 0 ? (
              <div className="work-grid">
                {works.map((work) => (
                  <WorkCard work={work} onOpen={openWork} key={work.workId} />
                ))}
              </div>
            ) : (
              <div className="no-results">
                <span aria-hidden="true">∅</span>
                <h3>No works match these criteria.</h3>
                <p>Try a broader search or remove one of the active filters.</p>
                <button className="button button-primary" type="button" onClick={clearFilters}>
                  Clear filters
                </button>
              </div>
            )}
          </section>
        </div>
      </main>

      <footer className="site-footer">
        <div>
          <strong>General Corpus</strong>
          <p>Readable historical editions with transparent paths back to their sources.</p>
        </div>
        <div className="footer-review">
          <p>
            Metadata reviewed through {catalog.metadataReviewedThrough ?? "an unrecorded date"}; lineage reviewed through {catalog.lineageReviewedThrough ?? "an unrecorded date"}. Rights notes are scoped statements, not blanket legal advice.
          </p>
          {catalog.publicationInventory && (
            <a href={assetUrl(catalog.publicationInventory.manifestPath)}>
              Publication snapshot · {catalog.publicationInventory.itemCount} PDFs · {catalog.publicationInventory.snapshotDate}
            </a>
          )}
        </div>
      </footer>

      {mobileFilters && (
        <div className="mobile-filter-overlay" role="dialog" aria-modal="true" aria-label="Catalog filters" onMouseDown={(event) => event.target === event.currentTarget && setMobileFilters(false)}>
          <FilterPanel
            catalog={catalog}
            filters={filters}
            mobile
            onChange={changeFilters}
            onClear={clearFilters}
            onClose={() => setMobileFilters(false)}
          />
        </div>
      )}

      {selectedWorkId && (
        <WorkDetail detail={detail} loading={detailLoading} error={detailError} onClose={closeWork} />
      )}
    </div>
  );
}
