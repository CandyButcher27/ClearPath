import React from 'react'
import { verificationResultsData } from '../data/mockData'
import { useScrollAnimation } from '../hooks/useScrollAnimation'
import { getReportUrl } from '../lib/api'
import type { FlagResult, VerificationResults } from '../types/api'

export interface ReadonlyVerificationResultsScreenProps {
  onNavigateHome: () => void
  results: VerificationResults | null
  jobId: string
}

// ---------------------------------------------------------------------------
// Build display points from the inconsistency_flags object
// ---------------------------------------------------------------------------
interface DisplayPoint {
  id: string
  title: string
  flagged: boolean
}

function buildPoints(results: VerificationResults | null): DisplayPoint[] {
  if (!results) {
    return verificationResultsData.points.map((p, i) => ({
      id: String(i + 1).padStart(2, '0'),
      title: p.title,
      flagged: false,
    }))
  }

  const flags = results.inconsistency_flags ?? {}
  const categories: [string, Record<string, FlagResult | null>][] = [
    ['Logistics', flags.logistics_flags ?? {}],
    ['Quantity & Weight', flags.quantity_weight_flags ?? {}],
    ['Product-Specific', flags.product_specific_flags ?? {}],
    ['Financial & Timing', flags.financial_timing_flags ?? {}],
  ]

  const points: DisplayPoint[] = []
  let counter = 1
  for (const [catLabel, catData] of categories) {
    const flagged = Object.values(catData).some(f => f?.is_flagged)
    points.push({
      id: String(counter).padStart(2, '0'),
      title: `${catLabel} Checks ${flagged ? '— Issues Detected' : '— All Clear'}`,
      flagged,
    })
    counter++
  }
  return points
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export const VerificationResultsScreen: React.FC<ReadonlyVerificationResultsScreenProps> = ({
  onNavigateHome,
  results,
  jobId,
}) => {
  const scrollY = useScrollAnimation()
  const points = buildPoints(results)

  const processId = results?.product_id ?? verificationResultsData.header.processId
  const category = results?.category_metadata?.applied_category ?? '—'
  const totalWeight = results?.normalized_aggregates?.total_weight_reported_kg ?? null
  const totalValue = results?.normalized_aggregates?.total_value ?? null
  const currency = results?.normalized_aggregates?.currency ?? 'USD'
  const inconsistencyFlags = results?.inconsistency_flags ?? {}
  const flaggedCount = results
    ? Object.values(inconsistencyFlags)
        .flatMap(c => Object.values(c ?? {}))
        .filter(f => f?.is_flagged).length
    : 0

  const handleDownloadReport = () => {
    window.open(getReportUrl(jobId), '_blank')
  }

  return (
    <div className="min-h-screen bg-surface text-on-surface selection:bg-secondary/20">
      <div className="fixed inset-0 z-0 grid-bg pointer-events-none" />

      <div className="wireframe-cube pointer-events-none fixed right-10 top-40 z-0 hidden opacity-20 lg:block">
        <div
          className="cube-inner"
          style={{ transform: `rotateX(${45 + scrollY * 0.15}deg) rotateY(${45 + scrollY * 0.075}deg) rotateZ(${scrollY * 0.03}deg)` }}
        >
          <div className="cube-face" style={{ transform: 'translateZ(30px)' }} />
          <div className="cube-face" style={{ transform: 'rotateY(90deg) translateZ(30px)' }} />
          <div className="cube-face" style={{ transform: 'rotateY(180deg) translateZ(30px)' }} />
          <div className="cube-face" style={{ transform: 'rotateY(-90deg) translateZ(30px)' }} />
          <div className="cube-face" style={{ transform: 'rotateX(90deg) translateZ(30px)' }} />
          <div className="cube-face" style={{ transform: 'rotateX(-90deg) translateZ(30px)' }} />
        </div>
      </div>

      <nav className="fixed top-0 z-50 flex h-20 w-full items-center justify-between border-b border-outline-variant/20 bg-surface/80 px-8 backdrop-blur-md">
        <div className="flex cursor-pointer items-center gap-2 text-2xl font-black uppercase tracking-tighter text-primary" onClick={onNavigateHome}>
          <span className="flex h-8 w-8 items-center justify-center bg-secondary text-xl text-white">C</span>
          Clear Path
        </div>
        <div className="hidden items-center gap-8 md:flex">
          <a className="font-medium text-on-surface-variant transition-colors hover:text-primary" href="#dash">Dashboard</a>
          <a className="font-medium text-on-surface-variant transition-colors hover:text-primary" href="#docs">Documents</a>
          <a className="font-medium text-on-surface-variant transition-colors hover:text-primary" href="#arch">Archives</a>
          <a className="border-b-2 border-secondary pb-1 font-inter font-bold tracking-tight text-primary" href="#reports">Reports</a>
        </div>
        <div className="flex items-center gap-6">
          <button onClick={onNavigateHome} className="bg-primary px-6 py-2.5 text-sm font-bold tracking-tight text-on-primary transition-all hover:bg-opacity-90">Verify New</button>
          <div className="h-10 w-10 overflow-hidden rounded-full border-2 border-outline-variant/30 bg-surface-container-high">
            <img alt="User profile" className="h-full w-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDh5xeDcwyCusmEDNp63h1VQZUFxeavqHnjNiaZeWOyMtq5y_ziSWoKIwB6GKQnnnXincMgsK1tuGmSp9YdIfgf23_L-H-TMuhHMqf7EIKvi3orBUz4_ooZV4ejNIFYcYGv4DV0cvO2FiBG_lO2ANEmHfZ1qnbXSA11UYNpmAzsYGpLqODVjK5NKHM5Jx17hG6hj42gzG8b3OE7U6N4vKmjg_ILOY_HAzQeU5VKzxm2s3qgmrrpl-bcpd6gFpjzF_xNbC6oaHj-GejM" />
          </div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-7xl px-8 pb-24 pt-32">
        <header className="animate-fade-up mb-20" style={{ transform: `translateY(${scrollY * 0.05}px)` }}>
          <div className="mb-6 flex items-start gap-4">
            <div className="rounded-sm bg-secondary p-1.5 shadow-lg shadow-secondary/20">
              <img src="/circle.png" alt="check circle" className="inline-block h-8 w-8 object-contain" />
            </div>
            <div className="flex flex-col">
              <span className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-secondary">
                Process ID: {processId}
              </span>
              <h1 className="text-7xl font-black uppercase leading-[0.9] tracking-tighter text-primary md:text-8xl">
                {verificationResultsData.header.title}
              </h1>
            </div>
          </div>
          <p className="mt-4 max-w-2xl border-l-4 border-secondary pl-6 text-lg leading-relaxed text-on-surface-variant">
            {results
              ? `${flaggedCount} inconsistency flag(s) detected across ${points.length} check categories.`
              : verificationResultsData.header.description}
          </p>
        </header>

        <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-12">
          {/* Left: check points */}
          <div className="stagger-children lg:col-span-8 space-y-4">
            {points.map((point, index) => (
              <div
                key={point.id}
                className={`reveal point-${index} group rounded-sm border-l-8 bg-surface-container-lowest p-8 shadow-sm transition-all duration-500 hover:bg-surface-container hover:shadow-xl ${
                  point.flagged ? 'border-secondary' : 'border-primary'
                }`}
                style={{ transform: `translateY(${index % 2 === 0 ? scrollY * 0.02 : scrollY * -0.015}px)` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant">Check Group {point.id}</span>
                    <h3 className={`text-2xl font-bold tracking-tight ${point.flagged ? 'text-secondary' : 'text-primary'}`}>
                      {point.title}
                    </h3>
                  </div>
                  <img
                    src={point.flagged ? '/circle.png' : '/ccircle.png'}
                    alt={point.flagged ? 'flagged' : 'verified'}
                    className="animated-check inline-block"
                    style={{
                      width: '32px', height: '32px', objectFit: 'contain',
                      animationDelay: `${0.1 + index * 0.1}s`,
                      filter: point.flagged ? 'hue-rotate(0deg)' : 'none',
                    }}
                  />
                </div>
              </div>
            ))}

            {/* Detailed flags table */}
            {results && flaggedCount > 0 && (
              <div className="mt-8 border border-secondary/20 bg-surface-container-lowest p-8">
                <h4 className="mb-4 text-xs font-black uppercase tracking-widest text-secondary">Detailed Flag Analysis</h4>
                <div className="space-y-3">
                  {Object.entries(inconsistencyFlags).flatMap(([catName, catData]) =>
                    Object.entries(catData ?? {})
                      .filter(([, f]) => f?.is_flagged)
                      .map(([flagName, flagData]) => (
                        <div key={`${catName}-${flagName}`} className="border-l-2 border-secondary/40 pl-4">
                          <span className="text-[10px] font-black uppercase tracking-widest text-secondary">
                            {flagName.replace(/_/g, ' ')}
                          </span>
                          <div className="mt-1 text-xs text-on-surface-variant">
                            {Object.entries(flagData as FlagResult)
                              .filter(([k]) => k !== 'is_flagged')
                              .slice(0, 3)
                              .map(([k, v]) => (
                                <span key={k} className="mr-3">
                                  <span className="font-bold">{k.replace(/_/g, ' ')}:</span>{' '}
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </span>
                              ))}
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right: sidebar */}
          <div className="scroll-reveal-left lg:col-span-4 sticky top-32 space-y-8">
            <div className="group relative overflow-hidden rounded-sm border border-white/8 bg-surface-container-high p-8 shadow-xl">
              <div className="absolute inset-0 bg-gradient-to-br from-surface-container-high via-surface-container-high to-secondary/10 opacity-50" />
              <div className="relative z-10">
                <h4 className="mb-6 text-[10px] font-bold uppercase tracking-[0.3em] text-on-surface-variant">Shipment Summary</h4>

                {results ? (
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-on-surface-variant text-[10px] font-bold uppercase">Category</span>
                      <span className="font-bold text-on-surface">{category}</span>
                    </div>
                    {totalWeight !== null && (
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant text-[10px] font-bold uppercase">Total Weight</span>
                        <span className="font-bold text-on-surface">{totalWeight.toFixed(1)} kg</span>
                      </div>
                    )}
                    {totalValue !== null && (
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant text-[10px] font-bold uppercase">Total Value</span>
                        <span className="font-bold text-on-surface">{currency} {totalValue.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between pt-2 border-t border-white/10">
                      <span className="text-on-surface-variant text-[10px] font-bold uppercase">Flags Raised</span>
                      <span className={`font-bold ${flaggedCount > 0 ? 'text-secondary' : 'text-emerald-400'}`}>
                        {flaggedCount}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="break-all font-mono text-sm leading-relaxed tracking-wider text-on-surface opacity-90">
                    {verificationResultsData.sidebar.hash}
                  </div>
                )}

                <div className="mt-8 border-t border-white/10 pt-8">
                  <div className="flex justify-between">
                    <span className="text-[10px] font-bold uppercase text-on-surface-variant">Job ID</span>
                    <span className="text-xs font-bold text-on-surface font-mono">{jobId.slice(0, 8)}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="group relative h-64 overflow-hidden rounded-sm border border-white/5 bg-primary shadow-2xl">
              <img
                alt="Industrial Hub"
                className="h-full w-full object-cover brightness-50 contrast-125 grayscale transition-transform duration-700 group-hover:scale-110"
                src={verificationResultsData.sidebar.hubImage}
              />

              <div className="scanning-overlay absolute inset-0 h-[20%] w-full animate-scan-line bg-[linear-gradient(transparent_0%,rgba(227,30,36,0.1)_50%,transparent_100%)] pointer-events-none" />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(0,0,0,0)_0%,rgba(0,0,0,0.6)_100%)]" />

              <div className="absolute bottom-4 left-4 right-4 z-20 flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-secondary shadow-[0_0_8px_#E31E24] animate-pulse" />
                  <p className="text-[9px] font-black uppercase tracking-[0.3em] text-white">Live Visual Confirmation</p>
                </div>
                <p className="text-xs font-bold text-white/80">Terminal Hub: Port Area 7G</p>
              </div>
            </div>

            <button
              onClick={handleDownloadReport}
              className="btn-glow relative w-full overflow-hidden rounded-sm bg-secondary py-5 text-sm font-black uppercase tracking-[0.2em] text-white shadow-[0_0_15px_rgba(227,30,36,0.2)] transition-all hover:bg-[#f12a31] hover:shadow-[0_0_30px_rgba(227,30,36,0.5)] active:scale-[0.98]"
            >
              Download Report PDF
            </button>
          </div>
        </div>
      </main>

      <footer className="relative z-10 w-full border-t border-outline-variant/20 bg-surface py-16">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-10 px-8 md:flex-row">
          <div className="flex items-center gap-2 text-xl font-black uppercase tracking-tighter text-primary">
            <span className="flex h-6 w-6 items-center justify-center bg-secondary text-xs text-white">C</span>
            CLEAR PATH
          </div>
          <div className="flex flex-wrap justify-center gap-10">
            <a className="font-inter text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant transition-colors hover:text-secondary" href="#sec">Security</a>
            <a className="font-inter text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant transition-colors hover:text-secondary" href="#tos">Terms of Service</a>
            <a className="font-inter text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant transition-colors hover:text-secondary" href="#api">API Documentation</a>
            <a className="font-inter text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant transition-colors hover:text-secondary" href="#support">Support</a>
          </div>
          <div className="font-inter text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant">
            (c) 2024 CLEAR PATH INDUSTRIAL. ALL RIGHTS RESERVED.
          </div>
        </div>
      </footer>
    </div>
  )
}
