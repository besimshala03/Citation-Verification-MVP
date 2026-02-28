import { create } from 'zustand'
import type { Citation, Project, ReferenceEntry, VerificationResult } from '../types'
import {
  createProject as apiCreateProject,
  deleteProject as apiDeleteProject,
  deleteReferencePaper as apiDeleteReferencePaper,
  getProjectDetail as apiGetProjectDetail,
  listProjects as apiListProjects,
  listReferences as apiListReferences,
  uploadDocument as apiUploadDocument,
  uploadReferencePaper as apiUploadReferencePaper,
  verifyCitation as apiVerifyCitation,
} from '../api/client'

interface AppState {
  // Screen routing
  screen: 'projects' | 'project-detail' | 'analysis'

  // Project list
  projects: Project[]
  loadingProjects: boolean

  // Current project
  currentProjectId: string | null
  currentProjectName: string | null
  documentId: string | null
  fileName: string | null
  referenceEntries: ReferenceEntry[]
  warning: string | null

  // Analysis state
  citations: Citation[]
  selectedCitationId: number | null
  verificationResults: Record<number, VerificationResult>
  loadingCitationId: number | null

  // Upload tracking
  uploadingEntryId: number | null

  // Actions — Projects
  fetchProjects: () => Promise<void>
  createProject: (name: string) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  openProject: (projectId: string) => Promise<void>

  // Actions — Document & References
  uploadDocument: (file: File) => Promise<void>
  uploadReferencePaper: (entryId: number, file: File) => Promise<void>
  deleteReferencePaper: (entryId: number) => Promise<void>
  refreshReferences: () => Promise<void>

  // Actions — Analysis
  goToAnalysis: () => void
  selectCitation: (id: number) => void
  verifyCitation: (id: number) => Promise<void>

  // Navigation
  goToProjects: () => void
  goToProjectDetail: () => void
  reset: () => void
}

export const useAppStore = create<AppState>((set, get) => ({
  screen: 'projects',
  projects: [],
  loadingProjects: false,
  currentProjectId: null,
  currentProjectName: null,
  documentId: null,
  fileName: null,
  referenceEntries: [],
  warning: null,
  citations: [],
  selectedCitationId: null,
  verificationResults: {},
  loadingCitationId: null,
  uploadingEntryId: null,

  // --- Projects ---

  fetchProjects: async () => {
    set({ loadingProjects: true })
    try {
      const projects = await apiListProjects()
      set({ projects, loadingProjects: false })
    } catch {
      set({ loadingProjects: false })
    }
  },

  createProject: async (name: string) => {
    const project = await apiCreateProject(name)
    // Navigate to the new project
    set({
      screen: 'project-detail',
      currentProjectId: project.id,
      currentProjectName: project.name,
      documentId: null,
      fileName: null,
      referenceEntries: [],
      citations: [],
      warning: null,
      verificationResults: {},
      selectedCitationId: null,
    })
  },

  deleteProject: async (projectId: string) => {
    await apiDeleteProject(projectId)
    // Refresh list
    get().fetchProjects()
  },

  openProject: async (projectId: string) => {
    const detail = await apiGetProjectDetail(projectId)
    set({
      screen: 'project-detail',
      currentProjectId: detail.id,
      currentProjectName: detail.name,
      documentId: detail.document?.id || null,
      fileName: detail.document?.filename || null,
      referenceEntries: detail.reference_entries,
      warning: detail.warning,
      verificationResults: {},
      selectedCitationId: null,
      loadingCitationId: null,
    })
  },

  // --- Document & References ---

  uploadDocument: async (file: File) => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    const data = await apiUploadDocument(currentProjectId, file)
    set({
      documentId: data.document_id,
      fileName: data.filename,
      referenceEntries: data.reference_entries,
      warning: data.warning,
      citations: [],
      verificationResults: {},
      selectedCitationId: null,
    })
  },

  uploadReferencePaper: async (entryId: number, file: File) => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    set({ uploadingEntryId: entryId })
    try {
      await apiUploadReferencePaper(currentProjectId, entryId, file)
      // Refresh reference list
      const refs = await apiListReferences(currentProjectId)
      set({ referenceEntries: refs, uploadingEntryId: null })
    } catch {
      set({ uploadingEntryId: null })
      throw new Error('Failed to upload reference paper')
    }
  },

  deleteReferencePaper: async (entryId: number) => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    await apiDeleteReferencePaper(currentProjectId, entryId)
    const refs = await apiListReferences(currentProjectId)
    set({ referenceEntries: refs })
  },

  refreshReferences: async () => {
    const { currentProjectId } = get()
    if (!currentProjectId) return
    const refs = await apiListReferences(currentProjectId)
    set({ referenceEntries: refs })
  },

  // --- Analysis ---

  goToAnalysis: () => {
    set({
      screen: 'analysis',
      selectedCitationId: null,
      verificationResults: {},
      loadingCitationId: null,
    })
  },

  selectCitation: (id: number) => {
    set({ selectedCitationId: id })
    const { verificationResults, loadingCitationId } = get()
    if (!verificationResults[id] && loadingCitationId === null) {
      get().verifyCitation(id)
    }
  },

  verifyCitation: async (id: number) => {
    const { currentProjectId, verificationResults } = get()
    if (!currentProjectId || verificationResults[id]) return

    set({ loadingCitationId: id })
    try {
      const result = await apiVerifyCitation(currentProjectId, id)
      set((state) => ({
        verificationResults: { ...state.verificationResults, [id]: result },
        loadingCitationId: null,
      }))
    } catch {
      set({ loadingCitationId: null })
    }
  },

  // --- Navigation ---

  goToProjects: () => {
    set({
      screen: 'projects',
      currentProjectId: null,
      currentProjectName: null,
      documentId: null,
      fileName: null,
      referenceEntries: [],
      citations: [],
      warning: null,
      verificationResults: {},
      selectedCitationId: null,
      loadingCitationId: null,
    })
  },

  goToProjectDetail: () => {
    const { currentProjectId } = get()
    if (currentProjectId) {
      get().openProject(currentProjectId)
    }
  },

  reset: () =>
    set({
      screen: 'projects',
      projects: [],
      loadingProjects: false,
      currentProjectId: null,
      currentProjectName: null,
      documentId: null,
      fileName: null,
      referenceEntries: [],
      warning: null,
      citations: [],
      selectedCitationId: null,
      verificationResults: {},
      loadingCitationId: null,
      uploadingEntryId: null,
    }),
}))

// Expose store for debugging (dev only)
if (import.meta.env.DEV) {
  ;(window as any).__store = useAppStore
}
