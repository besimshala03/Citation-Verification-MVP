import { useCallback, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'
import { frontendConfig } from '../config'
import type { ReferenceEntry } from '../types'

export function ProjectDetailScreen() {
  const currentProjectName = useAppStore((s) => s.currentProjectName)
  const documentId = useAppStore((s) => s.documentId)
  const fileName = useAppStore((s) => s.fileName)
  const referenceEntries = useAppStore((s) => s.referenceEntries)
  const warning = useAppStore((s) => s.warning)
  const uploadDocument = useAppStore((s) => s.uploadDocument)
  const uploadReferencePaper = useAppStore((s) => s.uploadReferencePaper)
  const deleteReferencePaper = useAppStore((s) => s.deleteReferencePaper)
  const uploadingEntryId = useAppStore((s) => s.uploadingEntryId)
  const goToProjects = useAppStore((s) => s.goToProjects)
  const goToAnalysis = useAppStore((s) => s.goToAnalysis)
  const appError = useAppStore((s) => s.appError)
  const authUser = useAppStore((s) => s.authUser)
  const logout = useAppStore((s) => s.logout)

  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  const uploadedCount = referenceEntries.filter((r) => r.status === 'uploaded').length

  const handleDocUpload = useCallback(
    async (file: File) => {
      const ext = file.name.toLowerCase()
      if (!frontendConfig.allowedMainExtensions.some((suffix) => ext.endsWith(suffix))) {
        setError('Only PDF and DOCX files are supported.')
        return
      }
      if (
        file.type &&
        !frontendConfig.allowedMainMimeTypes.includes(
          file.type as (typeof frontendConfig.allowedMainMimeTypes)[number],
        )
      ) {
        setError('Unsupported MIME type for document upload.')
        return
      }
      if (file.size > frontendConfig.maxMainDocumentBytes) {
        setError('Main document exceeds the 20MB size limit.')
        return
      }
      setError(null)
      setUploading(true)
      try {
        await uploadDocument(file)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [uploadDocument],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleDocUpload(file)
    },
    [handleDocUpload],
  )

  const onBrowseDoc = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,.docx'
    input.onchange = () => {
      const file = input.files?.[0]
      if (file) handleDocUpload(file)
    }
    input.click()
  }, [handleDocUpload])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen flex flex-col"
    >
      {/* Top bar */}
      <div className="flex items-center gap-4 px-6 py-3 border-b border-white/10 bg-white/[0.02]">
        <button
          onClick={goToProjects}
          className="text-gray-400 hover:text-white transition-colors text-sm flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Projects
        </button>
        <div className="h-4 w-px bg-white/10" />
        <h2 className="text-gray-200 text-sm font-medium truncate flex-1">
          {currentProjectName}
        </h2>
        <div className="flex items-center gap-2 shrink-0">
          <span className="hidden lg:block text-xs text-gray-400 max-w-[220px] truncate">
            {authUser?.email}
          </span>
          <button
            onClick={logout}
            className="px-2.5 py-1.5 rounded-lg bg-white/10 text-gray-200 hover:bg-white/20 text-xs"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6 max-w-4xl mx-auto w-full">
        {documentId && (
          <div className="flex justify-end mb-4">
            <button
              onClick={goToAnalysis}
              disabled={uploadedCount === 0}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all
                ${uploadedCount > 0
                  ? 'bg-amber-500 hover:bg-amber-400 text-black'
                  : 'bg-white/5 text-gray-600 cursor-not-allowed'
                }`}
              title={uploadedCount === 0 ? 'Upload at least one reference paper to analyze' : ''}
            >
              Analyze ({uploadedCount}/{referenceEntries.length} ready)
            </button>
          </div>
        )}

        {/* Document section */}
        <section className="mb-8">
          <h3 className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-3">
            Main Document
          </h3>
          {documentId ? (
            <div className="glass-card p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-gray-200 text-sm font-medium truncate">{fileName}</p>
                <p className="text-gray-500 text-xs">
                  {referenceEntries.length} references found • Click "Analyze" when ready
                </p>
              </div>
              <button
                onClick={onBrowseDoc}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1"
              >
                Replace
              </button>
            </div>
          ) : (
            <div
              onDrop={onDrop}
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onClick={onBrowseDoc}
              className={`glass-card p-10 flex flex-col items-center justify-center cursor-pointer
                transition-all duration-300
                ${dragging ? 'border-amber-400/60 shadow-[0_0_40px_rgba(245,158,11,0.3)]' : 'hover:border-white/20'}
                ${uploading ? 'pointer-events-none opacity-60' : ''}`}
            >
              {uploading ? (
                <>
                  <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-3" />
                  <p className="text-gray-400 text-sm">Analyzing document...</p>
                </>
              ) : (
                <>
                  <svg
                    className={`w-12 h-12 mb-3 transition-colors ${dragging ? 'text-amber-400' : 'text-gray-600'}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-gray-400 text-sm mb-1">
                    {dragging ? 'Drop your file here' : 'Drag & drop your PDF or DOCX'}
                  </p>
                  <p className="text-gray-600 text-xs">or click to browse</p>
                </>
              )}
            </div>
          )}

          {error && (
            <p className="text-red-400 text-xs mt-2">{error}</p>
          )}
          {appError && (
            <p className="text-red-400 text-xs mt-2">{appError}</p>
          )}
          {warning && (
            <p className="text-yellow-400/80 text-xs mt-2">{warning}</p>
          )}
        </section>

        {/* References section */}
        {documentId && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs text-gray-500 uppercase tracking-wider font-medium">
                References ({referenceEntries.length})
              </h3>
              {referenceEntries.length > 0 && (
                <span className="text-xs text-gray-500">
                  {uploadedCount} uploaded
                </span>
              )}
            </div>

            {referenceEntries.length === 0 ? (
              <div className="glass-card p-8 text-center">
                <p className="text-gray-500 text-sm">No references found in the document.</p>
              </div>
            ) : (
              <div className="space-y-2">
                <AnimatePresence>
                  {referenceEntries.map((entry, i) => (
                    <ReferenceCard
                      key={entry.id}
                      entry={entry}
                      index={i}
                      isUploading={uploadingEntryId === entry.id}
                      onUpload={(file) => uploadReferencePaper(entry.id, file)}
                      onDelete={() => deleteReferencePaper(entry.id)}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </section>
        )}
      </div>
    </motion.div>
  )
}

function ReferenceCard({
  entry,
  index,
  isUploading,
  onUpload,
  onDelete,
}: {
  entry: ReferenceEntry
  index: number
  isUploading: boolean
  onUpload: (file: File) => Promise<void>
  onDelete: () => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        if (!file.name.toLowerCase().endsWith(frontendConfig.allowedReferenceExtension)) {
          setUploadError('Only PDF files are supported.')
          e.target.value = ''
          return
        }
        if (file.type && file.type !== frontendConfig.allowedReferenceMimeType) {
          setUploadError('Unsupported MIME type for reference PDF upload.')
          e.target.value = ''
          return
        }
        if (file.size > frontendConfig.maxReferencePdfBytes) {
          setUploadError('Reference PDF exceeds the 50MB size limit.')
          e.target.value = ''
          return
        }
        setUploadError(null)
        try {
          await onUpload(file)
        } catch (err) {
          setUploadError(err instanceof Error ? err.message : 'Upload failed')
        }
        // Reset input so same file can be re-selected
        e.target.value = ''
      }
    },
    [onUpload],
  )

  const isUploaded = entry.status === 'uploaded'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.02, duration: 0.2 }}
      className="glass-card p-4"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        className="sr-only"
      />

      <div className="flex items-start gap-3">
        {/* Index badge */}
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 mt-0.5
          ${isUploaded ? 'bg-green-500/20 text-green-400' : 'bg-white/5 text-gray-500'}`}
        >
          {isUploaded ? '✓' : index + 1}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Entry metadata */}
          {entry.parsed_title && (
            <p className="text-gray-200 text-sm font-medium mb-0.5 leading-snug">
              {entry.parsed_title}
            </p>
          )}
          <p className="text-gray-500 text-xs mb-2 leading-relaxed line-clamp-2">
            {entry.parsed_author && `${entry.parsed_author}`}
            {entry.parsed_year && ` (${entry.parsed_year})`}
            {!entry.parsed_title && ` — ${entry.entry_text}`}
          </p>

          {/* Actions row */}
          <div className="flex items-center gap-2 flex-wrap">
            {isUploaded ? (
              <div className="flex items-center gap-2">
                <span className="text-xs px-2.5 py-1 rounded-lg bg-green-500/10 text-green-400 font-medium flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {entry.paper_filename}
                </span>
                <button
                  onClick={onDelete}
                  className="text-xs text-gray-600 hover:text-red-400 transition-colors p-1"
                  title="Remove paper"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <button
                onClick={handleFileSelect}
                disabled={isUploading}
                className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400
                           hover:bg-amber-500/20 transition-colors font-medium
                           disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center gap-1.5"
              >
                {isUploading ? (
                  <>
                    <div className="w-3 h-3 border border-amber-400 border-t-transparent rounded-full animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Upload PDF
                  </>
                )}
              </button>
            )}

            {/* Greyed-out AI button */}
            <button
              disabled
              className="text-xs px-3 py-1.5 rounded-lg bg-white/5 border border-white/5
                         text-gray-600 cursor-not-allowed flex items-center gap-1.5"
              title="Coming soon — automatic paper discovery using AI"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              Auto-find with AI
            </button>
          </div>

          {uploadError && (
            <p className="text-red-400 text-xs mt-2">{uploadError}</p>
          )}
        </div>
      </div>
    </motion.div>
  )
}
