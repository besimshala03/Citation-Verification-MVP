import { create } from 'zustand'
import type { Citation, VerificationResult } from '../types'
import { uploadFile as apiUpload, verifyCitation as apiVerify } from '../api/client'

interface AppState {
  // Screen state
  screen: 'upload' | 'analysis'

  // File state
  file: File | null
  fileId: string | null
  fileName: string | null

  // Citation state
  citations: Citation[]
  selectedCitationId: number | null
  verificationResults: Record<number, VerificationResult>
  loadingCitationId: number | null
  warning: string | null

  // Actions
  uploadFile: (file: File) => Promise<void>
  selectCitation: (id: number) => void
  verifyCitation: (id: number) => Promise<void>
  reset: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  screen: 'upload',
  file: null,
  fileId: null,
  fileName: null,
  citations: [],
  selectedCitationId: null,
  verificationResults: {},
  loadingCitationId: null,
  warning: null,

  uploadFile: async (file: File) => {
    set({ file })
    const data = await apiUpload(file)
    set({
      screen: 'analysis',
      fileId: data.file_id,
      fileName: data.document_name,
      citations: data.citations,
      warning: data.warning || null,
    })
  },

  selectCitation: (id: number) => {
    set({ selectedCitationId: id })
    // Auto-verify if not already verified
    const { verificationResults, loadingCitationId } = get()
    if (!verificationResults[id] && loadingCitationId === null) {
      get().verifyCitation(id)
    }
  },

  verifyCitation: async (id: number) => {
    const { fileId, verificationResults } = get()
    if (!fileId || verificationResults[id]) return
    set({ loadingCitationId: id })
    try {
      const result = await apiVerify(fileId, id)
      set((state) => ({
        verificationResults: { ...state.verificationResults, [id]: result },
        loadingCitationId: null,
      }))
    } catch {
      set({ loadingCitationId: null })
    }
  },

  reset: () =>
    set({
      screen: 'upload',
      file: null,
      fileId: null,
      fileName: null,
      citations: [],
      selectedCitationId: null,
      verificationResults: {},
      loadingCitationId: null,
      warning: null,
    }),
}))

// Expose store for debugging (dev only)
if (import.meta.env.DEV) {
  ;(window as any).__store = useAppStore
}
