import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'
import type { Project } from '../types'

export function ProjectListScreen() {
  const projects = useAppStore((s) => s.projects)
  const loadingProjects = useAppStore((s) => s.loadingProjects)
  const fetchProjects = useAppStore((s) => s.fetchProjects)
  const createProject = useAppStore((s) => s.createProject)
  const deleteProjectAction = useAppStore((s) => s.deleteProject)
  const openProject = useAppStore((s) => s.openProject)
  const appError = useAppStore((s) => s.appError)
  const authUser = useAppStore((s) => s.authUser)
  const logout = useAppStore((s) => s.logout)

  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleCreate = useCallback(async () => {
    if (!newName.trim() || newName.trim().length > 120) return
    setCreating(true)
    try {
      await createProject(newName.trim())
    } catch {
      setCreating(false)
    }
  }, [newName, createProject])

  const handleDelete = useCallback(async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation()
    if (deletingId) return
    setDeletingId(projectId)
    try {
      await deleteProjectAction(projectId)
    } finally {
      setDeletingId(null)
    }
  }, [deleteProjectAction, deletingId])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex flex-col items-center p-8"
    >
      <div className="w-full max-w-2xl flex items-center justify-end gap-2 mb-2">
        <span className="hidden sm:block text-xs text-gray-400 truncate max-w-[220px]">
          {authUser?.email}
        </span>
        <button
          onClick={logout}
          className="px-2.5 py-1.5 rounded-lg bg-white/10 text-gray-200 hover:bg-white/20 text-xs"
        >
          Logout
        </button>
      </div>

      {/* Header */}
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="text-center mb-10 mt-12"
      >
        <h1 className="text-4xl font-bold text-white mb-2">Citation Verifier</h1>
        <p className="text-gray-400 text-lg">
          Create a project to verify citations in academic documents
        </p>
      </motion.div>

      {/* Create project button / form */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="w-full max-w-2xl mb-8"
      >
        {showCreate ? (
          <div className="glass-card p-5 flex gap-3 items-center">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              placeholder="Project name..."
              autoFocus
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5
                         text-white text-sm placeholder-gray-500 outline-none
                         focus:border-amber-400/50 transition-colors"
            />
                <button
                  onClick={handleCreate}
                  disabled={creating || !newName.trim() || newName.trim().length > 120}
                  className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-black font-medium
                         text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => { setShowCreate(false); setNewName('') }}
              className="text-gray-400 hover:text-white transition-colors text-sm px-2"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowCreate(true)}
            className="glass-card w-full p-5 flex items-center justify-center gap-2
                       text-gray-400 hover:text-amber-400 hover:border-amber-400/30
                       transition-all duration-300 cursor-pointer group"
          >
            <svg className="w-5 h-5 transition-transform group-hover:scale-110" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="font-medium">Create New Project</span>
          </button>
        )}
      </motion.div>

      {/* Project list */}
      <div className="w-full max-w-2xl space-y-3">
        {appError && (
          <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            {appError}
          </div>
        )}
        {loadingProjects && projects.length === 0 ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : projects.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
              </svg>
            </div>
            <p className="text-gray-500 text-sm">No projects yet. Create one to get started.</p>
          </motion.div>
        ) : (
          <AnimatePresence>
            {projects.map((project, i) => (
              <ProjectCard
                key={project.id}
                project={project}
                index={i}
                onOpen={() => openProject(project.id)}
                onDelete={(e) => handleDelete(e, project.id)}
                isDeleting={deletingId === project.id}
              />
            ))}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  )
}

function ProjectCard({
  project,
  index,
  onOpen,
  onDelete,
  isDeleting,
}: {
  project: Project
  index: number
  onOpen: () => void
  onDelete: (e: React.MouseEvent) => void
  isDeleting: boolean
}) {
  const refCount = project.reference_count || 0
  const refsUploaded = project.references_uploaded || 0
  const hasDoc = Boolean(project.has_document)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      onClick={onOpen}
      className={`glass-card p-5 cursor-pointer transition-all duration-300
                  hover:border-white/20 hover:shadow-[0_0_30px_rgba(255,255,255,0.05)]
                  ${isDeleting ? 'opacity-50 pointer-events-none' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-medium text-base truncate mb-1">
            {project.name}
          </h3>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            {hasDoc ? (
              <>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  Document uploaded
                </span>
                <span>•</span>
                <span>
                  {refsUploaded}/{refCount} references
                </span>
                <span>•</span>
                <span>{project.citation_count} citations</span>
              </>
            ) : (
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                No document yet
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {refCount > 0 && (
            <div className="flex items-center gap-1">
              <div className="w-12 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-400 rounded-full transition-all"
                  style={{ width: `${refCount > 0 ? (refsUploaded / refCount) * 100 : 0}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 min-w-[2rem] text-right">
                {Math.round(refCount > 0 ? (refsUploaded / refCount) * 100 : 0)}%
              </span>
            </div>
          )}
          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10
                       transition-colors"
            title="Delete project"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </motion.div>
  )
}
