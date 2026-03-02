import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'
import { downloadExport, getExportCsvUrl, getExportPdfUrl } from '../api/client'
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
  const hasAnyResults = Object.keys(verificationResults).length > 0
  const [exportOpen, setExportOpen] = useState(false)
  const [exporting, setExporting] = useState(false)

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
        {/* Export dropdown */}
        <div className="relative">
          <button
            onClick={() => setExportOpen(!exportOpen)}
            disabled={!hasAnyResults || exporting}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5
              ${hasAnyResults
                ? 'bg-white/10 text-gray-200 hover:bg-white/20'
                : 'bg-white/5 text-gray-600 cursor-not-allowed'
              }`}
            title={hasAnyResults ? 'Export results' : 'Verify citations first to enable export'}
          >
            {exporting ? (
              <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
            Export
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {exportOpen && (
            <div className="absolute right-0 top-full mt-1 bg-gray-800 border border-white/10 rounded-lg shadow-xl z-50 min-w-[140px]">
              <button
                onClick={async () => {
                  if (!currentProjectId) return
                  setExportOpen(false)
                  setExporting(true)
                  try {
                    await downloadExport(getExportCsvUrl(currentProjectId), 'verification_results.csv')
                  } catch { /* silently handled */ }
                  setExporting(false)
                }}
                className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-white/10 rounded-t-lg flex items-center gap-2"
              >
                <svg className="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export CSV
              </button>
              <button
                onClick={async () => {
                  if (!currentProjectId) return
                  setExportOpen(false)
                  setExporting(true)
                  try {
                    await downloadExport(getExportPdfUrl(currentProjectId), 'verification_results.pdf')
                  } catch { /* silently handled */ }
                  setExporting(false)
                }}
                className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-white/10 rounded-b-lg flex items-center gap-2"
              >
                <svg className="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Export PDF
              </button>
            </div>
          )}
        </div>
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
