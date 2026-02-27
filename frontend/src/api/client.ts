import type { UploadResponse, VerificationResult } from '../types'

const BASE = '/api'

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

export async function verifyCitation(
  fileId: string,
  citationId: number,
): Promise<VerificationResult> {
  const res = await fetch(`${BASE}/verify-citation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId, citation_id: citationId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Verification failed' }))
    throw new Error(err.detail || 'Verification failed')
  }
  return res.json()
}

export function getFileUrl(fileId: string): string {
  return `${BASE}/file/${fileId}`
}
