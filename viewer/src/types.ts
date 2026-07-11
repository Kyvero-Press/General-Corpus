export type PublicationStatus = "available" | "unavailable";
export type MetadataStatus = "cataloged" | "pending";

export interface Publication {
  status: PublicationStatus;
  filename: string;
  path: string | null;
  externalUrl: string | null;
  bytes: number | null;
  sizeLabel: string | null;
  pages: number | null;
  pageSize: string | null;
  embeddedTitle: string | null;
  embeddedAuthor: string | null;
  sha256: string | null;
}

export interface LabeledCode {
  code: string;
  label: string;
}

export interface LabeledTerm {
  term: string;
  label: string;
}

export interface ResolvedPlace {
  label: string;
  relation: string;
}

export interface WorkCardRecord {
  workId: string;
  displayTitle: string;
  preferredTitle: string;
  translatedTitle: string | null;
  author: string;
  editor: string | null;
  dateDisplay: string;
  regionDisplay: string;
  form: string;
  languages: LabeledCode[];
  genres: LabeledTerm[];
  subjects: LabeledTerm[];
  tags: string[];
  regions: ResolvedPlace[];
  sourcePeriods: string[];
  publicationYear: number | null;
  summary: string;
  metadataStatus: MetadataStatus;
  metadataRecordStatus: string | null;
  lineageStatus: "available" | "missing";
  lastReviewed: string | null;
  publication: Publication;
  detailPath: string;
}

export interface FacetOption {
  value: string;
  label?: string;
  count: number;
}

export interface CatalogFacets {
  metadataStatuses: FacetOption[];
  pdfStatuses: FacetOption[];
  recordStatuses: FacetOption[];
  forms: FacetOption[];
  languages: FacetOption[];
  genres: FacetOption[];
  subjects: FacetOption[];
  tags: FacetOption[];
  regions: FacetOption[];
  sourcePeriods: FacetOption[];
}

export interface CatalogCounts {
  works: number;
  catalogedMetadata: number;
  lineageRecords: number;
  metadataPending: number;
  pdfsAvailable: number;
  pdfsUnavailable: number;
  publicationBytes: number;
}

export interface CatalogIndex {
  schemaVersion: string;
  catalogReviewedThrough: string | null;
  metadataReviewedThrough: string | null;
  lineageReviewedThrough: string | null;
  coverageNote: string | null;
  lineageCoverageNote: string | null;
  publicationInventory: {
    snapshotDate: string | null;
    itemCount: number;
    manifestPath: string;
  } | null;
  counts: CatalogCounts;
  facets: CatalogFacets;
  works: WorkCardRecord[];
}

export interface MetadataDetail {
  manifestId: string | null;
  recordStatus: string | null;
  lastReviewed: string | null;
  catalogingSubject: Record<string, unknown> | null;
  catalogSummary: Record<string, unknown> | null;
  titles: MetadataTitle[];
  responsibilities: Responsibility[];
  dateStatements: MetadataStatement[];
  placeStatements: MetadataStatement[];
  languageStatements: MetadataStatement[];
  formStatements: MetadataStatement[];
  genres: MetadataStatement[];
  subjects: MetadataStatement[];
  tags: string[];
  summaries: MetadataStatement[];
  extent: Record<string, unknown> | null;
  contentStructureStatus: string | null;
  contentParts: ContentPart[];
  openQuestions: QuestionRecord[];
  notes: string[];
}

export interface MetadataTitle {
  id?: string;
  type?: string;
  value?: string;
  language?: string;
  script?: string;
  scope?: ScopeRecord;
  notes?: string[];
}

export interface ScopeRecord {
  kind?: string;
  part_ids?: string[];
  description?: string;
}

export interface Responsibility {
  id?: string;
  role?: string;
  attribution_status?: string;
  display_name?: string;
  agentName?: string;
  scope?: ScopeRecord;
  notes?: string[];
}

export interface MetadataStatement {
  id?: string;
  type?: string;
  value?: string;
  display?: string;
  code?: string;
  label?: string;
  usage?: string;
  term?: string;
  description?: string;
  placeLabel?: string;
  primary?: boolean;
  scope?: ScopeRecord;
  normalized?: unknown;
  notes?: string[];
}

export interface ContentPart {
  id?: string;
  label?: string;
  type?: string;
  order?: number;
  extent?: Record<string, unknown>;
  scope?: ScopeRecord;
  summary?: string;
  description?: string;
  notes?: string[];
}

export interface QuestionRecord {
  id?: string;
  question?: string;
  status?: string;
  impact?: string;
  last_checked?: string;
  next_steps?: string[];
  notes?: string[];
}

export interface RightRecord {
  id?: string;
  entity?: string;
  access_id?: string;
  component?: string;
  jurisdiction?: string;
  copyright_status?: string;
  as_of?: string;
  basis?: string;
  rights_statement_uri?: string;
  contract_terms_status?: string;
  effective_until?: string;
  confidence?: string;
  notes?: string[];
}

export interface LocalCopyRecord {
  label: string;
  path: string;
  sourceUrl: string;
  sha256: string;
  bytes: number;
  sizeLabel: string | null;
  mediaType: string;
  downloadedOn: string;
  coverage: "complete" | "partial" | "metadata_only" | "unknown";
  retrievalMethod: "direct_download" | "iiif_bundle";
  sourceFileCount: number | null;
  bundleSourceKind: "iiif_presentation_manifest" | "image_url_inventory" | null;
  workPortion: WorkPortionRecord | null;
  notes: string[];
  available: boolean;
}

export interface WorkPortionRecord {
  label: string;
  locators: string[];
  startUrl: string | null;
  endUrl: string | null;
  notes: string[];
}

export interface AccessRecord {
  id: string | null;
  entityId: string;
  entityLabel: string;
  entityType: string;
  provider: string | null;
  resourceKind: string | null;
  status: string | null;
  accessMethod: string | null;
  url: string | null;
  alternateUrls: string[];
  contact: string | null;
  cost: string | null;
  format: string | null;
  lastChecked: string | null;
  notes: string[];
  localCopies: LocalCopyRecord[];
  rights: RightRecord[];
}

export interface LineageEntity {
  id: string;
  type: string | null;
  label: string | null;
  description: string | null;
  identifiers: Array<Record<string, unknown>>;
  bibliographic: Record<string, unknown> | null;
  holding: Record<string, unknown> | null;
  physicalDescription: Record<string, unknown> | null;
  dateStatements: MetadataStatement[];
  survivalStatus: string | null;
  notes: string[];
  access: AccessRecord[];
  rights: RightRecord[];
}

export interface LineageRelation {
  id: string | null;
  type: string | null;
  subjectId: string | null;
  subjectLabel: string | null;
  objectId: string | null;
  objectLabel: string | null;
  scope: RelationScope | null;
  assertion: AssertionRecord | null;
}

export interface RelationScopeEndpoint {
  kind?: string;
  description?: string;
  locators?: string[];
}

export interface RelationScope {
  subject?: RelationScopeEndpoint;
  object?: RelationScopeEndpoint;
  notes?: string;
}

export interface AssertionRecord {
  status?: string;
  confidence?: string;
  evidence_ids?: string[];
  notes?: string;
}

export interface LineageDetail {
  manifestId: string | null;
  recordStatus: string | null;
  lastReviewed: string | null;
  summary: string | null;
  entities: LineageEntity[];
  relations: LineageRelation[];
  sourceLinks: AccessRecord[];
  openQuestions: QuestionRecord[];
  reviewNotes: string[];
}

export interface WorkDetailRecord {
  schemaVersion: string;
  work: WorkCardRecord;
  metadata: MetadataDetail | null;
  lineage: LineageDetail | null;
  metadataManifestPath: string | null;
  lineageManifestPath: string | null;
}
