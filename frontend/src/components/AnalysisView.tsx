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
  const verifyAllCitations = useAppStore((s) => s.verifyAllCitations)
  const batchVerifying = useAppStore((s) => s.batchVerifying)
  const batchTotal = useAppStore((s) => s.batchTotal)
  const batchVerified = useAppStore((s) => s.batchVerified)
  const batchErrors = useAppStore((s) => s.batchErrors)
  const verificationResults = useAppStore((s) => s.verificationResults)
  const appError = useAppStore((s) => s.appError)
  const authUser = useAppStore((s) => s.authUser)
  const logout = useAppStore((s) => s.logout)

  const allVerified = citations.length > 0 && citations.every((c) => verificationResults[c.id])

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
        {/* Verify All button */}
        <button
          onClick={verifyAllCitations}
          disabled={batchVerifying || citations.length === 0 || allVerified}
          className={`ml-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5
            ${batchVerifying
              ? 'bg-amber-500/20 text-amber-400 cursor-wait'
              : allVerified
                ? 'bg-green-500/20 text-green-400 cursor-default'
                : 'bg-amber-500 hover:bg-amber-400 text-black'
            }`}
        >
          {batchVerifying ? (
            <>
              <div className="w-3 h-3 border border-amber-400 border-t-transparent rounded-full animate-spin" />
              Verifying...
            </>
          ) : allVerified ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              All Verified
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Verify All
            </>
          )}
        </button>
        <span className="hidden lg:block text-xs text-gray-400 ml-auto max-w-[220px] truncate">
          {authUser?.email}
        </span>
        <button
          onClick={logout}
          className="px-2.5 py-1.5 rounded-lg bg-white/10 text-gray-200 hover:bg-white/20 text-xs"
        >
          Logout
        </button>
      </div>
      {appError && (
        <div className="px-6 py-2 text-sm text-red-300 bg-red-500/10 border-b border-red-500/20">
          {appError}
        </div>
      )}
      {/* Batch verification progress bar */}
      {(batchVerifying || (batchTotal > 0 && batchVerified > 0)) && (
        <div className="px-6 py-2 border-b border-white/10 bg-white/[0.02]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-400">
              {batchVerifying
                ? 'Verifying all citations...'
                : `Verification complete: ${batchVerified} verified${batchErrors > 0 ? `, ${batchErrors} errors` : ''}`
              }
            </span>
            <span className="text-xs text-gray-500">
              {batchVerified}/{batchTotal}
            </span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: batchTotal > 0 ? `${(batchVerified / batchTotal) * 100}%` : '0%' }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              className={`h-full rounded-full ${batchErrors > 0 ? 'bg-yellow-500' : 'bg-green-500'}`}
            />
          </div>
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
