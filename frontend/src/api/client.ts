import type {
  Citation,
  DocumentUploadResponse,
  Project,
  ProjectDetail,
  ReferenceEntry,
  ReferenceUploadResponse,
  VerificationResult,
} from '../types'

const BASE = '/api'

async function extractError(res: Response): Promise<Error> {
  const err = await res.json().catch(() => ({ detail: 'Request failed' }))
  return new Error(err.detail || 'Request failed')
}

// --- Projects ---

export async function createProject(name: string): Promise<Project> {
  const res = await fetch(`${BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw await extractError(res)
  return res.json()
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${BASE}/projects`)
  if (!res.ok) throw await extractError(res)
  const data = await res.json()
  return data.projects
}

export async function getProjectDetail(projectId: string): Promise<ProjectDetail> {
  const res = await fetch(`${BASE}/projects/${projectId}`)
  if (!res.ok) throw await extractError(res)
  return res.json()
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${BASE}/projects/${projectId}`, { method: 'DELETE' })
  if (!res.ok) throw await extractError(res)
}

// --- Document ---

export async function uploadDocument(
  projectId: string,
  file: File,
): Promise<DocumentUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/projects/${projectId}/document`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw await extractError(res)
  return res.json()
}

export function getDocumentUrl(projectId: string): string {
  return `${BASE}/projects/${projectId}/document/file`
}

// --- References ---

export async function listReferences(
  projectId: string,
): Promise<ReferenceEntry[]> {
  const res = await fetch(`${BASE}/projects/${projectId}/references`)
  if (!res.ok) throw await extractError(res)
  const data = await res.json()
  return data.references
}

export async function uploadReferencePaper(
  projectId: string,
  entryId: number,
  file: File,
): Promise<ReferenceUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(
    `${BASE}/projects/${projectId}/references/${entryId}/paper`,
    { method: 'POST', body: form },
  )
  if (!res.ok) throw await extractError(res)
  return res.json()
}

export async function deleteReferencePaper(
  projectId: string,
  entryId: number,
): Promise<void> {
  const res = await fetch(
    `${BASE}/projects/${projectId}/references/${entryId}/paper`,
    { method: 'DELETE' },
  )
  if (!res.ok) throw await extractError(res)
}

// --- Verification ---

export async function verifyCitation(
  projectId: string,
  citationId: number,
): Promise<VerificationResult> {
  const res = await fetch(`${BASE}/projects/${projectId}/verify-citation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ citation_id: citationId }),
  })
  if (!res.ok) throw await extractError(res)
  return res.json()
}

export async function listCitations(projectId: string): Promise<Citation[]> {
  const res = await fetch(`${BASE}/projects/${projectId}/citations`)
  if (!res.ok) throw await extractError(res)
  const data = await res.json()
  return data.citations
}
