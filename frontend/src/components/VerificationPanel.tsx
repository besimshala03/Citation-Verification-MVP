import { motion, AnimatePresence } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'
import type { VerificationResult } from '../types'

const LABEL_CONFIG: Record<string, { color: string; glow: string; icon: string }> = {
  SUPPORTS: { color: 'text-green-400', glow: 'glow-supports', icon: '\u2713' },
  CONTRADICTS: { color: 'text-red-400', glow: 'glow-contradicts', icon: '\u2717' },
  UNCERTAIN: { color: 'text-yellow-400', glow: 'glow-uncertain', icon: '?' },
  NOT_RELEVANT: { color: 'text-gray-400', glow: 'glow-irrelevant', icon: '\u2014' },
}

export function VerificationPanel() {
  const selectedCitationId = useAppStore((s) => s.selectedCitationId)
  const loadingCitationId = useAppStore((s) => s.loadingCitationId)
  const verificationResults = useAppStore((s) => s.verificationResults)
  const citations = useAppStore((s) => s.citations)

  const isLoading = loadingCitationId !== null
  const result = selectedCitationId !== null ? verificationResults[selectedCitationId] : null
  const citation = selectedCitationId !== null
    ? citations.find((c) => c.id === selectedCitationId)
    : null

  return (
    <div className="h-full p-5 flex flex-col">
      <AnimatePresence mode="wait">
        {selectedCitationId === null ? (
          <EmptyState key="empty" />
        ) : isLoading ? (
          <LoadingState key="loading" />
        ) : result ? (
          <ResultView key={`result-${selectedCitationId}`} result={result} />
        ) : citation ? (
          <PreVerifyState key="pre" citation={citation.citation_text} />
        ) : null}
      </AnimatePresence>
    </div>
  )
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex-1 flex flex-col items-center justify-center text-center"
    >
      <div className="w-16 h-16 mb-4 rounded-full bg-white/5 flex items-center justify-center">
        <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zM12 2.25V4.5m5.834.166l-1.591 1.591M20.25 10.5H18M7.757 14.743l-1.59 1.59M6 10.5H3.75m4.007-4.243l-1.59-1.59" />
        </svg>
      </div>
      <p className="text-gray-500 text-sm">Click a highlighted citation in the PDF to verify it</p>
    </motion.div>
  )
}

function LoadingState() {
  const steps = ['Loading reference paper...', 'Analyzing content...', 'Matching passages...', 'Evaluating claim...']
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex-1 flex flex-col items-center justify-center"
    >
      <div className="w-12 h-12 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mb-6" />
      <div className="space-y-3 w-full max-w-xs">
        {steps.map((step, i) => (
          <motion.div
            key={step}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.3, duration: 0.3 }}
            className="flex items-center gap-3"
          >
            <div className="w-2 h-2 rounded-full bg-amber-400/60 animate-pulse" />
            <span className="text-gray-400 text-sm">{step}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

function PreVerifyState({ citation }: { citation: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex-1 flex flex-col items-center justify-center text-center"
    >
      <p className="text-gray-400 text-sm">
        Verifying <span className="text-amber-400 font-medium">{citation}</span>...
      </p>
    </motion.div>
  )
}

function ResultView({ result }: { result: VerificationResult }) {
  const config = LABEL_CONFIG[result.evaluation.label] || LABEL_CONFIG.UNCERTAIN

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-4 overflow-auto"
    >
      {/* Verdict badge */}
      <div className={`glass-card p-5 ${config.glow}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className={`text-2xl font-bold ${config.color}`}>{config.icon}</span>
            <span className={`text-lg font-semibold ${config.color}`}>
              {result.evaluation.label.replace('_', ' ')}
            </span>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500 mb-1">Confidence</div>
            <div className={`text-sm font-mono font-bold ${config.color}`}>
              {Math.round(result.evaluation.confidence * 100)}%
            </div>
          </div>
        </div>
        {/* Confidence bar */}
        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${result.evaluation.confidence * 100}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            className="h-full rounded-full"
            style={{
              backgroundColor:
                result.evaluation.label === 'SUPPORTS' ? '#22c55e'
                : result.evaluation.label === 'CONTRADICTS' ? '#ef4444'
                : result.evaluation.label === 'UNCERTAIN' ? '#eab308'
                : '#6b7280',
            }}
          />
        </div>
        <p className="text-gray-300 text-sm mt-3 leading-relaxed">
          {result.evaluation.explanation}
        </p>
      </div>

      {/* Citing paragraph */}
      <div className="glass-card p-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-medium">
          Citing Paragraph
        </div>
        <p className="text-gray-300 text-sm leading-relaxed max-h-40 overflow-auto">
          {result.citing_paragraph}
        </p>
      </div>

      {/* Source passage */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider font-medium">
            Source Passage
          </div>
          {result.evidence_page && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-medium">
              p. {result.evidence_page}
            </span>
          )}
        </div>
        {result.matched_passage ? (
          <p className="text-gray-300 text-sm leading-relaxed max-h-40 overflow-auto">
            {result.matched_passage}
          </p>
        ) : (
          <p className="text-gray-500 text-sm italic">No passage available</p>
        )}
        {result.evidence_why && (
          <p className="text-gray-400 text-xs mt-3 leading-relaxed">
            Why this evidence matters: {result.evidence_why}
          </p>
        )}
      </div>

      {/* Paper metadata */}
      {result.paper_metadata && (
        <div className="glass-card p-4">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-medium">
            Paper Details
          </div>
          <p className="text-gray-200 text-sm font-medium mb-1">
            {result.paper_metadata.title}
          </p>
          <p className="text-gray-400 text-xs mb-2">
            {result.paper_metadata.authors.join(', ')}
            {result.paper_metadata.year && ` (${result.paper_metadata.year})`}
          </p>
          <div className="flex gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                result.source_type === 'pdf'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-500/20 text-gray-400'
              }`}
            >
              {result.source_type === 'pdf'
                ? 'Full Text'
                : 'Reference Not Uploaded'}
            </span>
            {result.bibliography_match && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-medium">
                Bibliography Matched
              </span>
            )}
          </div>
        </div>
      )}
    </motion.div>
  )
}
