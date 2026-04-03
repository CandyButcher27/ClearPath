import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createStatusStream, parseCompleteEvent } from '../lib/api'
import type { LogLine, VerificationResults } from '../types/api'

type LogLevel = 'SYSTEM' | 'INFO' | 'OK' | 'WARN' | 'HASH'

const levelColor: Record<LogLevel, string> = {
  OK: 'text-emerald-400',
  WARN: 'text-amber-400',
  HASH: 'text-[#e90716]',
  SYSTEM: 'text-white/60',
  INFO: 'text-sky-400/70',
}

export interface ReadonlyProcessingScreenProps {
  jobId: string
  onComplete: (results: VerificationResults | null) => void
}

export const ProcessingScreen: React.FC<ReadonlyProcessingScreenProps> = ({ jobId, onComplete }) => {
  const [visibleLines, setVisibleLines] = useState<LogLine[]>([])
  const [phase, setPhase] = useState<'running' | 'complete'>('running')
  const [cursorBlink, setCursorBlink] = useState(true)
  const [totalExpected] = useState(20) // approximate for progress bar

  const terminalRef = useRef<HTMLDivElement | null>(null)
  const resultsRef = useRef<VerificationResults | null>(null)

  const progressPct = useMemo(
    () => Math.min((visibleLines.length / totalExpected) * 100, 95),
    [visibleLines.length, totalExpected],
  )

  // Cursor blink interval
  useEffect(() => {
    const id = window.setInterval(() => setCursorBlink(p => !p), 530)
    return () => window.clearInterval(id)
  }, [])

  // Connect SSE stream
  useEffect(() => {
    const es = createStatusStream(jobId)

    es.onmessage = (event) => {
      try {
        const line = JSON.parse(event.data) as LogLine
        setVisibleLines(prev => [...prev, line])
      } catch {
        // ignore malformed
      }
    }

    es.addEventListener('complete', (event: Event) => {
      const messageEvent = event as MessageEvent
      const payload = parseCompleteEvent(messageEvent.data)
      resultsRef.current = payload.results
      setPhase('complete')
      es.close()
      window.setTimeout(() => onComplete(resultsRef.current), 1200)
    })

    es.addEventListener('ping', () => { /* keep-alive, ignore */ })

    es.onerror = () => {
      // Connection error — treat as complete with no results
      if (phase !== 'complete') {
        setPhase('complete')
        es.close()
        window.setTimeout(() => onComplete(null), 1200)
      }
    }

    return () => es.close()
  }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [visibleLines, cursorBlink])

  return (
    <div className="min-h-screen bg-[#0d0d0f] px-4 py-10 text-[#c8c8d8]">
      <div className="relative mx-auto w-full max-w-[860px] border border-white/8 bg-[#111114] shadow-[0_32px_80px_rgba(0,0,0,0.6)]">
        <div className="flex items-center gap-3 border-b border-white/10 px-5 py-3">
          <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
          <div className="h-2.5 w-2.5 rounded-full bg-white/25" />
          <div className="h-2.5 w-2.5 rounded-full bg-white/25" />
          <span className="ml-3 font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
            session {jobId.slice(0, 8)} :: clearpath verification
          </span>
        </div>

        <div
          ref={terminalRef}
          className="h-[420px] overflow-y-auto px-5 py-4 font-mono text-sm leading-relaxed [&::-webkit-scrollbar-thumb]:bg-secondary/40 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:w-1.5"
        >
          {visibleLines.map((line, index) => (
            <div key={`${line.timestamp}-${index}`} className="animate-log-line whitespace-pre-wrap break-words">
              <span className="text-white/25">{line.timestamp}</span>{' '}
              <span className={levelColor[line.level as LogLevel] ?? 'text-white/50'}>[{line.level}]</span>{' '}
              <span className="text-[#c8c8d8]">{line.message}</span>
            </div>
          ))}

          {phase === 'running' ? (
            <div className="mt-1 flex items-center gap-2">
              <span className="text-white/35">[SYSTEM]</span>
              <span className="text-white/50">awaiting pipeline…</span>
              <span className={`h-4 w-2 bg-secondary transition-opacity ${cursorBlink ? 'opacity-100' : 'opacity-20'}`} />
            </div>
          ) : null}
        </div>

        <div className="border-t border-white/10 px-5 py-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.15em] text-white/55">
            {phase === 'complete'
              ? 'Processing complete'
              : `Processing ${visibleLines.length} operations…`}
          </div>
          <div className="h-1.5 w-full bg-white/10">
            <div
              className="h-full bg-secondary transition-all duration-500"
              style={{ width: phase === 'complete' ? '100%' : `${progressPct}%` }}
            />
          </div>
        </div>

        {phase === 'complete' ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0d0d0f]/80 backdrop-blur-sm">
            <span className="text-6xl font-black uppercase tracking-[0.18em] text-secondary">Verified</span>
          </div>
        ) : null}
      </div>
    </div>
  )
}
