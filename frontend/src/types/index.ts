// --- Project types ---

export interface Project {
  id: string
  name: string
  created_at: string
  updated_at: string
  has_document: boolean
  reference_count: number
  references_uploaded: number
  citation_count: number
}

export interface User {
  id: string
  email: string
  is_verified: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface RegisterResponse {
  message: string
  email: string
}

export interface ReferenceEntry {
  id: number
  entry_text: string
  parsed_author: string | null
  parsed_year: string | null
  parsed_title: string | null
  status: 'pending' | 'uploaded'
  paper_filename: string | null
}

export interface DocumentUploadResponse {
  document_id: string
  filename: string
  citation_count: number
  reference_entries: ReferenceEntry[]
  document_summary?: string | null
  warning: string | null
}

export interface ProjectDetail {
  id: string
  name: string
  document: {
    id: string
    filename: string
  } | null
  reference_entries: ReferenceEntry[]
  citation_count: number
  document_summary?: string | null
  warning: string | null
}

export interface ReferenceUploadResponse {
  paper_id: string
  reference_entry_id: number
  filename: string
  text_length: number
  status: string
}

// --- Citation & Verification types ---

export interface Citation {
  id: number
  citation_text: string
  author: string
  year: string
  citing_paragraph: string
  bibliography_match: string | null
  reference_entry_id: number | null
  verification_label?: string | null
}

export interface PaperMetadata {
  title: string
  authors: string[]
  year: number | null
}

export interface Evaluation {
  label: 'SUPPORTS' | 'CONTRADICTS' | 'NOT_RELEVANT' | 'UNCERTAIN'
  explanation: string
  confidence: number
}

export interface VerificationResult {
  citation_text: string
  author: string
  year: string
  citing_paragraph: string
  bibliography_match: string | null
  paper_found: boolean
  paper_metadata: PaperMetadata | null
  source_type: 'pdf' | 'not_uploaded' | 'not_found'
  matched_passage: string | null
  evidence_page?: number | null
  evidence_why?: string | null
  evaluation: Evaluation
}
