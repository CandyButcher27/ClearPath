import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ApiResult } from '../App'

function useCountUp(target: number, duration = 900): number {
  const [value, setValue] = useState(0)
  useEffect(() => {
    let rafId: number
    const start = performance.now()
    const frame = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      setValue(Math.round(target * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) rafId = requestAnimationFrame(frame)
    }
    rafId = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(rafId)
  }, [target, duration])
  return value
}

export interface ReadonlyVerificationResultsScreenProps {
  result: ApiResult | null
  onNavigateHome: () => void
}

function pct(v: unknown): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '0%'
  return `${Math.round(v)}%`
}

export const VerificationResultsScreen: React.FC<ReadonlyVerificationResultsScreenProps> = ({ result, onNavigateHome }) => {
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [hasGeneratedReport, setHasGeneratedReport] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const hasAutoTriggeredRef = useRef(false)

  const sessionId = result?.session_id ?? 'N/A'
  const normalized = result?.normalized ?? {}
  const telemetry = result?.telemetry ?? {}
  const explainability = result?.explainability ?? {}
  const explainItems = (explainability.items ?? []).filter(Boolean)
  const explainSummary = explainability.summary ?? {}
  const kpis = telemetry.kpis ?? {}
  const extraction = telemetry.extraction ?? {}

  const animRisk = useCountUp(Math.round(Number(kpis.risk_score ?? 0)))
  const animChecksPassed = useCountUp(Math.round(Number(kpis.checks_passed ?? 0)))
  const animTotal = useCountUp(Math.round(Number(kpis.total_checks ?? 0)))
  const animTimeSaved = useCountUp(Math.round(Number(kpis.estimated_time_saved_minutes ?? 0) * 10))
  const animCompleteness = useCountUp(Math.round(Number(kpis.completeness_index ?? explainSummary.completeness_index ?? 0)))

  const toggleItem = (id: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id) } else { next.add(id) }
      return next
    })
  }

  const operationsBrief = useMemo(() => {
    const category = String(((normalized as Record<string, unknown>)?.category_metadata as Record<string, unknown>)?.applied_category ?? 'General')
    const totalChecks = Number(explainSummary.total_checks ?? 0)
    const flagged = Number(explainSummary.flagged_checks ?? 0)
    const safe = Math.max(0, totalChecks - flagged)
    return {
      title: `${category} shipment review complete`,
      body: `Pipeline completed ${totalChecks} automated checks. ${safe} passed cleanly and ${flagged} require review.`,
      nextAction: flagged > 0 ? 'Review highlighted evidence before dispatch approval.' : 'Proceed to final certificate and dispatch.',
    }
  }, [normalized, explainSummary])

  const handleGenerateReport = useCallback(async () => {
    if (!result?.normalized) {
      setReportError('No normalized result available to generate report.')
      return
    }

    try {
      setIsGeneratingReport(true)
      setReportError(null)

      const res = await fetch('http://localhost:5000/api/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ normalized: result.normalized }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.error || `HTTP ${res.status}`)
      }

      const blob = await res.blob()
      const productId = String((result.normalized as Record<string, unknown>)?.product_id ?? 'shipment')
      const fileName = `report_${productId}.pdf`
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setHasGeneratedReport(true)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      if (/failed to fetch|networkerror|load failed/i.test(message)) {
        setReportError(
          `Could not reach backend report endpoint (http://localhost:5000/api/generate-report). ` +
          `Current frontend origin: ${window.location.origin}.`,
        )
      } else {
        setReportError(message)
      }
    } finally {
      setIsGeneratingReport(false)
    }
  }, [result])

  useEffect(() => {
    if (!result?.normalized) return
    if (hasAutoTriggeredRef.current) return
    hasAutoTriggeredRef.current = true
    void handleGenerateReport()
  }, [result, handleGenerateReport])

  return (
    <div className="ux-shell min-h-screen text-zinc-100">
      <div className="mx-auto max-w-7xl px-5 pb-20 pt-10">
        <header className="mb-8 grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Verification report</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight">Operations Trust Dashboard</h1>
            <p className="mt-3 max-w-3xl text-zinc-300">
              Session {sessionId} completed. Review explainability evidence, business KPIs, and recommended actions before release.
            </p>
          </div>
          <button
            onClick={onNavigateHome}
            className="rounded-lg border border-white/20 bg-white/5 px-5 py-3 text-sm font-medium text-zinc-100 transition hover:bg-white/10"
          >
            Verify New Shipment
          </button>
        </header>

        <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="glass-panel p-5">
            <p className="label">Risk Score</p>
            <p className={`metric ${animRisk > 50 ? 'text-rose-400' : animRisk > 20 ? 'text-amber-400' : 'text-emerald-400'}`}>{animRisk}</p>
          </div>
          <div className="glass-panel p-5">
            <p className="label">Checks Passed</p>
            <p className="metric">{animChecksPassed}/{animTotal}</p>
          </div>
          <div className="glass-panel p-5">
            <p className="label">Time Saved</p>
            <p className="metric">{(animTimeSaved / 10).toFixed(1)} min</p>
          </div>
          <div className="glass-panel p-5">
            <p className="label">Completeness</p>
            <p className="metric">{animCompleteness}%</p>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.9fr]">
          <div className="space-y-6">
            <section className="glass-panel p-6">
              <h2 className="section-title">Operations Brief</h2>
              <p className="mt-3 text-xl font-medium text-zinc-100">{operationsBrief.title}</p>
              <p className="mt-2 text-zinc-300">{operationsBrief.body}</p>
              <p className="mt-4 rounded-md border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-200">
                Next action: {operationsBrief.nextAction}
              </p>
            </section>

            <section className="glass-panel p-6">
              <h2 className="section-title">
                Issue Evidence
                <span className="ml-2 text-xs font-normal text-zinc-400">
                  ({explainItems.filter((i) => i?.is_flagged).length} flagged / {explainItems.length} total)
                </span>
              </h2>
              <div className="mt-4 space-y-2">
                {explainItems.length === 0 ? (
                  <div className="rounded-md border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-emerald-200">
                    No inconsistencies detected.
                  </div>
                ) : (
                  explainItems.map((item, idx) => {
                    const id = String(item.id ?? idx)
                    const isExpanded = expandedItems.has(id)
                    const isFlagged = Boolean(item?.is_flagged)
                    return (
                      <article
                        key={id}
                        className={`rounded-lg border bg-black/25 overflow-hidden transition-all ${isFlagged ? 'border-rose-500/30' : 'border-white/10'}`}
                      >
                        <button
                          onClick={() => toggleItem(id)}
                          className="flex w-full items-center justify-between px-4 py-3 text-left"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`rounded px-2 py-0.5 text-xs uppercase tracking-wider ${isFlagged ? 'bg-rose-500/20 text-rose-200' : 'bg-emerald-500/20 text-emerald-200'}`}>
                              {isFlagged ? String(item.severity ?? 'medium') : 'pass'}
                            </span>
                            <span className="text-sm font-medium text-zinc-100">
                              {String(item.flag_name ?? 'unknown').replaceAll('_', ' ')}
                            </span>
                          </div>
                          <span className="ml-4 text-xs text-zinc-500">{isExpanded ? '▲' : '▼'}</span>
                        </button>
                        {isExpanded && (
                          <div className="border-t border-white/10 px-4 pb-4 pt-3">
                            <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-xs uppercase tracking-wider text-indigo-200">
                              confidence {pct((Number(item.confidence ?? 0) || 0) * 100)}
                            </span>
                            <p className="mt-2 text-sm text-zinc-300">{String(item.rule ?? '')}</p>
                            <p className="mt-1 text-xs text-zinc-400">Threshold: {String(item.threshold ?? 'rule-specific')}</p>
                            <div className="mt-3 space-y-1 text-xs text-zinc-300">
                              {(item.evidence ?? []).map((ev: { path?: unknown; value?: unknown }, i: number) => (
                                <div key={i} className="rounded border border-white/10 bg-white/5 px-2 py-1">
                                  <span className="text-cyan-300">{String(ev.path ?? '')}</span>: {String(ev.value ?? '')}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </article>
                    )
                  })
                )}
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="glass-panel p-6">
              <h2 className="section-title">Decision Trace</h2>
              <div className="mt-3 space-y-2 text-sm">
                <p className="trace-row"><span>Extraction coverage</span><strong>{pct((Number(extraction.coverage_ratio ?? 0) || 0) * 100)}</strong></p>
                <p className="trace-row"><span>Parse retries</span><strong>{Math.round(Number(extraction.parse_retries ?? 0))}</strong></p>
                <p className="trace-row"><span>Fallback used</span><strong>{extraction.fallback_used ? 'yes' : 'no'}</strong></p>
                <p className="trace-row"><span>Total checks</span><strong>{Math.round(Number(explainSummary.total_checks ?? 0))}</strong></p>
                <p className="trace-row"><span>Flagged checks</span><strong>{Math.round(Number(explainSummary.flagged_checks ?? 0))}</strong></p>
              </div>
            </section>

            <section className="glass-panel p-6">
              <h2 className="section-title">Shipment Metadata</h2>
              <div className="mt-3 space-y-2 text-sm text-zinc-300">
                <p className="trace-row"><span>Product ID</span><strong>{String((normalized as Record<string, unknown>).product_id ?? 'N/A')}</strong></p>
                <p className="trace-row"><span>Runtime</span><strong>{Math.round(Number(telemetry.timing?.total_duration_ms ?? 0))} ms</strong></p>
                <p className="trace-row"><span>Chars extracted</span><strong>{Math.round(Number(extraction.chars_extracted ?? 0))}</strong></p>
              </div>
            </section>

            <section className="glass-panel p-6">
              <h2 className="section-title">Final Certificate</h2>
              <button
                onClick={handleGenerateReport}
                disabled={isGeneratingReport}
                className="mt-3 w-full rounded-lg bg-gradient-to-r from-indigo-500 via-cyan-500 to-fuchsia-500 px-4 py-3 text-sm font-semibold text-black transition hover:brightness-110 disabled:opacity-60"
              >
                {isGeneratingReport ? 'Generating Report...' : hasGeneratedReport ? 'Download Again' : 'Download Certificate'}
              </button>
              {reportError ? (
                <div className="mt-3 rounded border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                  {reportError}
                </div>
              ) : null}
            </section>
          </aside>
        </div>
      </div>
    </div>
  )
}

