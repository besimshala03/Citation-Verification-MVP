import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'
import { PdfViewer } from './pdf/PdfViewer'
import { VerificationPanel } from './VerificationPanel'

export function AnalysisView() {
  const fileName = useAppStore((s) => s.fileName)
  const citations = useAppStore((s) => s.citations)
  const currentProjectId = useAppStore((s) => s.currentProjectId)
  const goToProjectDetail = useAppStore((s) => s.goToProjectDetail)
  const fetchCitations = useAppStore((s) => s.fetchCitations)
  const appError = useAppStore((s) => s.appError)

  // Fetch citations when entering analysis view
  useEffect(() => {
    if (!currentProjectId) return
    fetchCitations()
  }, [currentProjectId, fetchCitations])

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="h-screen flex flex-col"
    >
      {/* Top bar */}
      <div className="flex items-center gap-4 px-6 py-3 border-b border-white/10 bg-white/[0.02]">
        <button
          onClick={goToProjectDetail}
          className="text-gray-400 hover:text-white transition-colors text-sm flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>
        <div className="h-4 w-px bg-white/10" />
        <h2 className="text-gray-200 text-sm font-medium truncate">{fileName}</h2>
        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-medium">
          {citations.length} citation{citations.length !== 1 ? 's' : ''}
        </span>
      </div>
      {appError && (
        <div className="px-6 py-2 text-sm text-red-300 bg-red-500/10 border-b border-red-500/20">
          {appError}
        </div>
      )}

      {/* Split layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: PDF viewer */}
        <div className="w-[60%] overflow-auto border-r border-white/10 bg-black/20">
          <PdfViewer />
        </div>

        {/* Right: Verification panel */}
        <div className="w-[40%] overflow-auto">
          <VerificationPanel />
        </div>
      </div>
    </motion.div>
  )
}
