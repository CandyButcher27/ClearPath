import React, { useEffect, useMemo, useRef, useState } from 'react'
import type { UploadedFiles, ApiResult } from '../App'

type LogLevel = 'SYSTEM' | 'INFO' | 'OK' | 'WARN' | 'HASH'

interface LogLine {
  timestamp: string
  level: LogLevel
  phase: string
  message: string
}

export interface ReadonlyProcessingScreenProps {
  files: UploadedFiles
  onComplete: (result: ApiResult) => void
  onError: () => void
  onCancel: () => void
}

const SYNTHETIC_FALLBACK: Array<Omit<LogLine, 'timestamp'>> = [
  { level: 'SYSTEM', phase: 'init', message: 'Provisioning verification worker...' },
  { level: 'INFO', phase: 'extract', message: 'Scanning uploaded files and validating structure...' },
  { level: 'INFO', phase: 'extract', message: 'Document OCR and layout extraction in progress...' },
  { level: 'INFO', phase: 'structure', message: 'Applying schema-driven parsing and field mapping...' },
  { level: 'HASH', phase: 'normalize', message: 'Computing integrity signatures and cross-check hashes...' },
  { level: 'OK', phase: 'complete', message: 'Final consistency checks passed. Preparing results...' },
]

const levelColor: Record<LogLevel, string> = {
  OK: 'text-emerald-400',
  WARN: 'text-amber-400',
  HASH: 'text-cyan-300',
  SYSTEM: 'text-zinc-300',
  INFO: 'text-indigo-200',
}

function nowTime() {
  const d = new Date()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  const ms = String(d.getMilliseconds()).padStart(3, '0')
  return `${h}:${m}:${s}.${ms}`
}

export const ProcessingScreen: React.FC<ReadonlyProcessingScreenProps> = ({ files, onComplete, onError, onCancel }) => {
  const [logLines, setLogLines] = useState<LogLine[]>([])
  const [requestPending, setRequestPending] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState('Preparing verification pipeline...')
  const [cursorBlink, setCursorBlink] = useState(true)
  const [streamConnected, setStreamConnected] = useState(false)
  const [usingFallback, setUsingFallback] = useState(false)

  const terminalRef = useRef<HTMLDivElement | null>(null)
  const fallbackIdxRef = useRef(0)
  const fallbackTimerRef = useRef<number | null>(null)
  const requestDoneRef = useRef(false)
  const hasStartedRef = useRef(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const progressPct = useMemo(() => {
    const phases = new Set(logLines.map((l) => l.phase))
    const score = Math.min(phases.size * 18, 100)
    return requestPending ? score : 100
  }, [logLines, requestPending])

  useEffect(() => {
    const cursorInterval = window.setInterval(() => setCursorBlink((p) => !p), 480)
    return () => window.clearInterval(cursorInterval)
  }, [])

  useEffect(() => {
    if (!terminalRef.current) return
    terminalRef.current.scrollTop = terminalRef.current.scrollHeight
  }, [logLines, cursorBlink])

  useEffect(() => {
    if (hasStartedRef.current) return
    hasStartedRef.current = true

    const sessionId = crypto.randomUUID().replace(/-/g, '').slice(0, 12)
    const pushLog = (entry: LogLine) => setLogLines((prev) => [...prev, entry])

    const startFallback = () => {
      if (usingFallback || requestDoneRef.current) return
      setUsingFallback(true)
      setStatusMessage('Live backend stream unavailable. Showing adaptive fallback logs...')
      fallbackTimerRef.current = window.setInterval(() => {
        if (requestDoneRef.current) {
          if (fallbackTimerRef.current) window.clearInterval(fallbackTimerRef.current)
          return
        }
        const template = SYNTHETIC_FALLBACK[fallbackIdxRef.current % SYNTHETIC_FALLBACK.length]
        fallbackIdxRef.current += 1
        pushLog({
          timestamp: nowTime(),
          level: template.level,
          phase: template.phase,
          message: template.message,
        })
      }, 850)
    }

    try {
      const es = new EventSource(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/process-shipment/logs/${sessionId}`)
      eventSourceRef.current = es

      const fallbackGuard = window.setTimeout(() => {
        if (!streamConnected && !requestDoneRef.current) startFallback()
      }, 1800)

      es.onopen = () => {
        setStreamConnected(true)
        setStatusMessage('Live processing stream connected...')
        window.clearTimeout(fallbackGuard)
      }

      es.onmessage = (event) => {
        if (!event.data) return
        try {
          const parsed = JSON.parse(event.data) as LogLine
          if (!parsed.message) return
          pushLog({
            timestamp: parsed.timestamp ? new Date(parsed.timestamp).toLocaleTimeString('en-US', { hour12: false }) : nowTime(),
            level: (parsed.level as LogLevel) ?? 'INFO',
            phase: parsed.phase ?? 'system',
            message: parsed.message,
          })
          setStatusMessage(parsed.message)
        } catch {
          // ignore malformed keepalive payloads
        }
      }

      es.addEventListener('status', (event) => {
        const data = JSON.parse((event as MessageEvent).data || '{}') as { status?: string }
        if (data.status === 'done') setStatusMessage('Verification complete. Building results view...')
      })

      es.onerror = () => {
        if (!requestDoneRef.current) startFallback()
      }
    } catch {
      startFallback()
    }

    const formData = new FormData()
    formData.append('session_id', sessionId)
    formData.append('bill_of_lading', files.bill_of_lading!)
    formData.append('invoice', files.invoice!)
    formData.append('packing_list', files.packing_list!)

    const submit = async () => {
      try {
        setStatusMessage('Submitting payload to backend...')
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/process-shipment`, { method: 'POST', body: formData })
        const data = await res.json()
        if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`)
        requestDoneRef.current = true
        setRequestPending(false)
        setStatusMessage('Backend response received. Preparing dashboard...')
        window.setTimeout(() => onComplete(data as ApiResult), 700)
      } catch (err) {
        requestDoneRef.current = true
        setRequestPending(false)
        const msg = err instanceof Error ? err.message : String(err)
        setApiError(msg)
        setStatusMessage('Processing failed. See error below.')
        window.setTimeout(() => onError(), 3000)
      } finally {
        if (fallbackTimerRef.current) window.clearInterval(fallbackTimerRef.current)
        if (eventSourceRef.current) eventSourceRef.current.close()
      }
    }

    void submit()

    return () => {
      if (fallbackTimerRef.current) window.clearInterval(fallbackTimerRef.current)
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }, [files, onComplete, onError, onCancel, streamConnected, usingFallback])

  return (
    <div className="ux-shell min-h-screen px-4 py-10 text-zinc-100">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">ClearPath Runtime</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">Live Verification Pipeline</h1>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right text-xs text-zinc-400">
              <p>stream: {streamConnected ? 'backend-live' : usingFallback ? 'fallback-sim' : 'connecting...'}</p>
              <p>mode: dark ops console</p>
            </div>
            {requestPending && (
              <button
                onClick={() => {
                  if (fallbackTimerRef.current) window.clearInterval(fallbackTimerRef.current)
                  if (eventSourceRef.current) eventSourceRef.current.close()
                  onCancel()
                }}
                className="rounded border border-white/20 bg-white/5 px-4 py-2 text-xs text-zinc-400 transition hover:bg-white/10 hover:text-zinc-100"
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        <div className="glass-panel overflow-hidden border border-white/10">
          <div className="flex items-center gap-2 border-b border-white/10 bg-black/30 px-4 py-3">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <span className="ml-3 text-[11px] uppercase tracking-[0.25em] text-zinc-400">processing terminal</span>
          </div>

          <div ref={terminalRef} className="h-[420px] overflow-y-auto px-5 py-4 font-mono text-sm leading-relaxed">
            {logLines.map((line, idx) => (
              <div key={`${line.timestamp}-${idx}`} className="animate-fade-up whitespace-pre-wrap break-words">
                <span className="text-zinc-500">{line.timestamp}</span>{' '}
                <span className={levelColor[line.level]}>[{line.level}]</span>{' '}
                <span className="text-zinc-200">{line.message}</span>
              </div>
            ))}
            <div className="mt-2 flex items-center gap-2 text-zinc-400">
              <span>[SYSTEM]</span>
              <span>awaiting pipeline update</span>
              <span className={`h-4 w-2 bg-cyan-400 transition-opacity ${cursorBlink ? 'opacity-100' : 'opacity-15'}`} />
            </div>
          </div>

          <div className="border-t border-white/10 px-5 py-4">
            <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.2em] text-zinc-400">
              <span>Pipeline Progress</span>
              <span>{Math.round(progressPct)}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
              <div className="h-full bg-gradient-to-r from-cyan-500 via-indigo-500 to-fuchsia-500 transition-all duration-500" style={{ width: `${progressPct}%` }} />
            </div>
            <p className="mt-3 text-sm text-zinc-300">{statusMessage}</p>
            {apiError ? (
              <p className="mt-2 rounded border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{apiError}</p>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

