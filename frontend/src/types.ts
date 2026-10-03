export interface BoundingBox {
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Field {
  name: string;
  value: unknown;
  confidence: number;
  bbox: BoundingBox | null;
  corrected: boolean;
}

export interface LineItem {
  fields: Record<string, Field>;
}

export interface TextLine {
  text: string;
  confidence: number;
  bbox: BoundingBox | null;
}

export interface QRCode {
  data: string;
  bbox: BoundingBox | null;
  image: string | null;
}

export interface Extraction {
  doc_type: string;
  engine: string;
  fields: Record<string, Field>;
  line_items: LineItem[];
  full_text: TextLine[];
  qr_codes: QRCode[];
  table_columns: string[];
}

export interface RuleResult {
  rule_id: string;
  description: string;
  severity: "critical" | "warning";
  passed: boolean;
  detail: string;
}

export interface SubDocumentResult {
  index: number;
  doc_type: string;
  workflow: string;
  engine: string;
  extraction: Extraction;
  rule_results: RuleResult[];
  min_confidence: number;
  route: "auto_approved" | "needs_review" | "rejected";
  route_reasons: string[];
}

export interface DocumentResult {
  id: string;
  source_name: string;
  image_url?: string | null;
  sub_documents: SubDocumentResult[];
  owner?: string | null;
  created_at?: string | null;
  folder_id?: string | null;
  approved?: boolean;
}
