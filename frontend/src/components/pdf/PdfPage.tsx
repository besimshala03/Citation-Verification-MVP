import { useCallback, useEffect, useRef, useState } from 'react'
import { Page } from 'react-pdf'
import { useAppStore } from '../../stores/useAppStore'

interface Props {
  pageNumber: number
  width: number
}

export function PdfPage({ pageNumber, width }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const citations = useAppStore((s) => s.citations)
  const selectedCitationId = useAppStore((s) => s.selectedCitationId)
  const verificationResults = useAppStore((s) => s.verificationResults)
  const selectCitation = useAppStore((s) => s.selectCitation)
  const [textLayerReady, setTextLayerReady] = useState(false)

  const highlightCitations = useCallback(() => {
    const container = containerRef.current
    if (!container) return

    // Remove old overlays
    container.querySelectorAll('.citation-highlight').forEach((el) => el.remove())

    const textLayer = container.querySelector('.react-pdf__Page__textContent')
    if (!textLayer) return

    // Collect all text spans and build a character-to-span map
    const spans = Array.from(textLayer.querySelectorAll('span'))
    if (!spans.length) return

    const fullText = spans.map((s) => s.textContent || '').join('')

    // Track which character ranges we've already highlighted
    const used = new Set<string>()

    for (const citation of citations) {
      const citText = citation.citation_text
      // Find all occurrences of this citation text in the page text
      let searchFrom = 0
      while (true) {
        const idx = fullText.indexOf(citText, searchFrom)
        if (idx === -1) break

        const rangeKey = `${idx}-${idx + citText.length}`
        if (used.has(rangeKey)) {
          searchFrom = idx + 1
          continue
        }
        used.add(rangeKey)

        // Find which spans this range covers
        const rects = getSpanRects(spans, idx, idx + citText.length, textLayer as HTMLElement)
        for (const rect of rects) {
          const overlay = document.createElement('div')
          overlay.className = getOverlayClass(citation.id, selectedCitationId, verificationResults)
          overlay.style.left = `${rect.left}px`
          overlay.style.top = `${rect.top}px`
          overlay.style.width = `${rect.width}px`
          overlay.style.height = `${rect.height}px`
          overlay.dataset.citationId = String(citation.id)
          overlay.addEventListener('click', (e) => {
            e.stopPropagation()
            selectCitation(citation.id)
          })
          textLayer.appendChild(overlay)
        }

        searchFrom = idx + citText.length
      }
    }
  }, [citations, selectedCitationId, verificationResults, selectCitation])

  // Re-run highlights when verification results or selection changes
  useEffect(() => {
    if (textLayerReady) {
      highlightCitations()
    }
  }, [textLayerReady, highlightCitations])

  return (
    <div ref={containerRef} className="shadow-2xl mb-2">
      <Page
        pageNumber={pageNumber}
        width={width}
        renderTextLayer={true}
        renderAnnotationLayer={true}
        onRenderTextLayerSuccess={() => {
          setTextLayerReady(true)
          highlightCitations()
        }}
      />
    </div>
  )
}

function getSpanRects(
  spans: HTMLSpanElement[],
  charStart: number,
  charEnd: number,
  textLayer: HTMLElement,
): { left: number; top: number; width: number; height: number }[] {
  const layerRect = textLayer.getBoundingClientRect()
  const rects: { left: number; top: number; width: number; height: number }[] = []
  let charIndex = 0

  for (const span of spans) {
    const text = span.textContent || ''
    const spanStart = charIndex
    const spanEnd = charIndex + text.length
    charIndex = spanEnd

    if (spanEnd <= charStart || spanStart >= charEnd) continue

    // Use Range API for precise character-level bounding rects
    const textNode = span.firstChild
    if (!textNode) continue

    const overlapStart = Math.max(charStart - spanStart, 0)
    const overlapEnd = Math.min(charEnd - spanStart, text.length)

    const range = document.createRange()
    range.setStart(textNode, overlapStart)
    range.setEnd(textNode, overlapEnd)

    const rangeRect = range.getBoundingClientRect()
    if (rangeRect.width > 0 && rangeRect.height > 0) {
      rects.push({
        left: rangeRect.left - layerRect.left,
        top: rangeRect.top - layerRect.top,
        width: rangeRect.width,
        height: rangeRect.height,
      })
    }
  }

  return mergeRects(rects)
}

function mergeRects(
  rects: { left: number; top: number; width: number; height: number }[],
): { left: number; top: number; width: number; height: number }[] {
  if (rects.length <= 1) return rects
  // Merge horizontally adjacent rects on the same line
  const sorted = rects.sort((a, b) => a.top - b.top || a.left - b.left)
  const merged: typeof rects = [sorted[0]]
  for (let i = 1; i < sorted.length; i++) {
    const prev = merged[merged.length - 1]
    const curr = sorted[i]
    // Same line (within 2px tolerance) and close horizontally
    if (Math.abs(curr.top - prev.top) < 2 && curr.left - (prev.left + prev.width) < 5) {
      prev.width = curr.left + curr.width - prev.left
      prev.height = Math.max(prev.height, curr.height)
    } else {
      merged.push(curr)
    }
  }
  return merged
}

function getOverlayClass(
  citationId: number,
  selectedId: number | null,
  results: Record<number, { evaluation: { label: string } }>,
): string {
  const base = 'citation-highlight'
  const result = results[citationId]
  if (result) {
    const label = result.evaluation.label.toLowerCase()
    return `${base} citation-highlight--${label}`
  }
  if (citationId === selectedId) {
    return `${base} citation-highlight--selected`
  }
  return `${base} citation-highlight--default`
}
