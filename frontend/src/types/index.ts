export interface Citation {
  id: number
  citation_text: string
  author: string
  year: string
  citing_paragraph: string
  bibliography_match: string | null
}

export interface UploadResponse {
  file_id: string
  document_name: string
  citations: Citation[]
  warning?: string
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
  source_type: 'pdf' | 'abstract_only' | 'not_found'
  matched_passage: string | null
  evaluation: Evaluation
}
