import type {
  CatalogIndex,
  Publication,
  WorkDetailRecord,
} from "./types";

export function assetUrl(path: string): string {
  return new URL(path, document.baseURI).toString();
}

export function safeExternalHttpUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    if (url.username || url.password) return null;
    return url.toString();
  } catch {
    return null;
  }
}

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(assetUrl(path), {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Could not load ${path} (${response.status})`);
  }
  return (await response.json()) as T;
}

export function loadCatalog(signal?: AbortSignal): Promise<CatalogIndex> {
  return fetchJson<CatalogIndex>("catalog/index.json", signal);
}

export function loadWorkDetail(
  path: string,
  signal?: AbortSignal,
): Promise<WorkDetailRecord> {
  return fetchJson<WorkDetailRecord>(path, signal);
}

export interface PublicationLink {
  url: string;
  isLocal: boolean;
}

export function publicationLink(
  publication: Publication,
): PublicationLink | null {
  if (publication.status !== "available") return null;
  if (publication.externalUrl) {
    const url = safeExternalHttpUrl(publication.externalUrl);
    return url ? { url, isLocal: false } : null;
  }
  if (publication.path) {
    return { url: assetUrl(publication.path), isLocal: true };
  }
  // The development server maps only exact, top-level dist filenames to this
  // route. Production catalogs never depend on this fallback: the release
  // build regenerates its data with --copy-pdfs.
  if (import.meta.env.DEV && publication.filename) {
    return {
      url: assetUrl(`publication-pdfs/${encodeURIComponent(publication.filename)}`),
      isLocal: true,
    };
  }
  return null;
}
