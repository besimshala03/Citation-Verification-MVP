import { create } from 'zustand'
import type { Citation, Project, ReferenceEntry, User, VerificationResult } from '../types'
import {
  createProject as apiCreateProject,
  deleteProject as apiDeleteProject,
  deleteReferencePaper as apiDeleteReferencePaper,
  getProjectDetail as apiGetProjectDetail,
  getMe as apiGetMe,
  listProjects as apiListProjects,
  listCitations as apiListCitations,
  listReferences as apiListReferences,
  login as apiLogin,
  resendVerification as apiResendVerification,
  register as apiRegister,
  setAuthToken,
  verifyEmail as apiVerifyEmail,
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
  appError: string | null
  authUser: User | null
  authToken: string | null
  authLoading: boolean
  pendingVerificationEmail: string | null

  // Actions — Projects
  fetchProjects: () => Promise<void>
  initializeAuth: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  verifyEmail: (email: string, code: string) => Promise<void>
  resendVerification: (email: string) => Promise<void>
  logout: () => void
  createProject: (name: string) => Promise<void>
  deleteProject: (projectId: string) => Promise<void>
  openProject: (projectId: string) => Promise<void>

  // Actions — Document & References
  uploadDocument: (file: File) => Promise<void>
  uploadReferencePaper: (entryId: number, file: File) => Promise<void>
  deleteReferencePaper: (entryId: number) => Promise<void>
  refreshReferences: () => Promise<void>
  fetchCitations: () => Promise<void>

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
  appError: null,
  authUser: null,
  authToken: null,
  authLoading: false,
  pendingVerificationEmail: null,

  initializeAuth: async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setAuthToken(null)
      return
    }
    set({ authLoading: true })
    try {
      setAuthToken(token)
      const me = await apiGetMe()
      set({ authToken: token, authUser: me.user, appError: null })
    } catch {
      localStorage.removeItem('auth_token')
      setAuthToken(null)
      set({ authToken: null, authUser: null })
    } finally {
      set({ authLoading: false })
    }
  },

  login: async (email: string, password: string) => {
    set({ authLoading: true })
    try {
      const data = await apiLogin(email, password)
      localStorage.setItem('auth_token', data.access_token)
      setAuthToken(data.access_token)
      set({
        authToken: data.access_token,
        authUser: data.user,
        pendingVerificationEmail: null,
        appError: null,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Login failed'
      set({
        appError: msg,
        pendingVerificationEmail: msg.includes('Email not verified') ? email.trim() : null,
      })
      throw e
    } finally {
      set({ authLoading: false })
    }
  },

  register: async (email: string, password: string) => {
    set({ authLoading: true })
    try {
      const data = await apiRegister(email, password)
      set({
        pendingVerificationEmail: data.email,
        appError: data.message,
      })
    } catch (e) {
      set({ appError: e instanceof Error ? e.message : 'Registration failed' })
      throw e
    } finally {
      set({ authLoading: false })
    }
  },

  verifyEmail: async (email: string, code: string) => {
    set({ authLoading: true })
    try {
      const data = await apiVerifyEmail(email, code)
      localStorage.setItem('auth_token', data.access_token)
      setAuthToken(data.access_token)
      set({
        authToken: data.access_token,
        authUser: data.user,
        pendingVerificationEmail: null,
        appError: null,
      })
    } catch (e) {
      set({ appError: e instanceof Error ? e.message : 'Email verification failed' })
      throw e
    } finally {
      set({ authLoading: false })
    }
  },

  resendVerification: async (email: string) => {
    set({ authLoading: true })
    try {
      const data = await apiResendVerification(email)
      set({ appError: data.message })
    } catch (e) {
      set({ appError: e instanceof Error ? e.message : 'Failed to resend verification code' })
      throw e
    } finally {
      set({ authLoading: false })
    }
  },

  logout: () => {
    localStorage.removeItem('auth_token')
    setAuthToken(null)
    set({
      authToken: null,
      authUser: null,
      pendingVerificationEmail: null,
      screen: 'projects',
      projects: [],
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
    })
  },

  // --- Projects ---

  fetchProjects: async () => {
    set({ loadingProjects: true })
    try {
      const projects = await apiListProjects()
      set({ projects, loadingProjects: false, appError: null })
    } catch (e) {
      set({
        loadingProjects: false,
        appError: e instanceof Error ? e.message : 'Failed to load projects',
      })
    }
  },

  createProject: async (name: string) => {
    try {
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
        appError: null,
      })
    } catch (e) {
      set({ appError: e instanceof Error ? e.message : 'Failed to create project' })
      throw e
    }
  },

  deleteProject: async (projectId: string) => {
    try {
      await apiDeleteProject(projectId)
      // Refresh list
      get().fetchProjects()
      set({ appError: null })
    } catch (e) {
      set({ appError: e instanceof Error ? e.message : 'Failed to delete project' })
      throw e
    }
  },

  openProject: async (projectId: string) => {
    try {
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
        appError: null,
      })
    } catch (e) {
      set({ appError: e instanceof Error ? e.message : 'Failed to open project' })
      throw e
    }
  },

  // --- Document & References ---

  uploadDocument: async (file: File) => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    if (file.size > 20 * 1024 * 1024) {
      throw new Error('Main document exceeds the 20MB size limit')
    }

    const data = await apiUploadDocument(currentProjectId, file)
    set({
      documentId: data.document_id,
      fileName: data.filename,
      referenceEntries: data.reference_entries,
      warning: data.warning,
      citations: [],
      verificationResults: {},
      selectedCitationId: null,
      appError: null,
    })
  },

  uploadReferencePaper: async (entryId: number, file: File) => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      throw new Error('Only PDF files are accepted for reference papers')
    }
    if (file.size > 50 * 1024 * 1024) {
      throw new Error('Reference PDF exceeds the 50MB size limit')
    }

    set({ uploadingEntryId: entryId })
    try {
      await apiUploadReferencePaper(currentProjectId, entryId, file)
      // Refresh reference list
      const refs = await apiListReferences(currentProjectId)
      set({ referenceEntries: refs, uploadingEntryId: null, appError: null })
    } catch (e) {
      set({
        uploadingEntryId: null,
        appError: e instanceof Error ? e.message : 'Failed to upload reference paper',
      })
      throw (e instanceof Error ? e : new Error('Failed to upload reference paper'))
    }
  },

  deleteReferencePaper: async (entryId: number) => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    await apiDeleteReferencePaper(currentProjectId, entryId)
    const refs = await apiListReferences(currentProjectId)
    set({ referenceEntries: refs, appError: null })
  },

  refreshReferences: async () => {
    const { currentProjectId } = get()
    if (!currentProjectId) return
    const refs = await apiListReferences(currentProjectId)
    set({ referenceEntries: refs, appError: null })
  },

  fetchCitations: async () => {
    const { currentProjectId } = get()
    if (!currentProjectId) return

    try {
      const citations = await apiListCitations(currentProjectId)
      set({ citations, appError: null })
    } catch (e) {
      set({
        appError: e instanceof Error ? e.message : 'Failed to load citations',
      })
    }
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
        appError: null,
      }))
    } catch (e) {
      set({
        loadingCitationId: null,
        appError: e instanceof Error ? e.message : 'Failed to verify citation',
      })
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
      appError: null,
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
      appError: null,
      authUser: null,
      authToken: null,
      authLoading: false,
      pendingVerificationEmail: null,
    }),
}))

// Expose store for debugging (dev only)
if (import.meta.env.DEV) {
  ;(window as any).__store = useAppStore
}
