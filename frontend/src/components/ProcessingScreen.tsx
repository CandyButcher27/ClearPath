import React, { useEffect, useMemo, useRef, useState } from 'react'

type LogLevel = 'SYSTEM' | 'INFO' | 'OK' | 'WARN' | 'HASH'

interface LogLine {
  timestamp: string
  level: LogLevel
  message: string
  delay: number
}

export interface ReadonlyProcessingScreenProps {
  onComplete: () => void
}

const LOG_LINES: LogLine[] = [
  { timestamp: '14:22:01.003', level: 'SYSTEM', message: 'ClearPath Verification Engine v3.1.4 -- initializing', delay: 200 },
  { timestamp: '14:22:01.011', level: 'INFO', message: 'Session ID: CP-992-X | Region: EU-WEST-2', delay: 120 },
  { timestamp: '14:22:01.089', level: 'INFO', message: 'Received 3 document payloads -- staging ingestion queue', delay: 300 },
  { timestamp: '14:22:01.201', level: 'INFO', message: 'Extracting metadata: BillOfLading_RU92841B.pdf', delay: 400 },
  { timestamp: '14:22:01.598', level: 'INFO', message: 'OCR pipeline: 847 tokens parsed, confidence 99.7%', delay: 350 },
  { timestamp: '14:22:01.950', level: 'OK', message: 'Bill of Lading structure validated -- ISO 28005 compliant', delay: 250 },
  { timestamp: '14:22:02.203', level: 'INFO', message: 'Extracting metadata: CommercialInvoice_EU2024.pdf', delay: 450 },
  { timestamp: '14:22:02.651', level: 'INFO', message: 'VAT registry cross-reference: checking 14 line items', delay: 600 },
  { timestamp: '14:22:03.254', level: 'WARN', message: 'Line item 7: currency notation ambiguity -- applying EUR normalization', delay: 500 },
  { timestamp: '14:22:03.757', level: 'OK', message: 'Invoice VAT compliance verified -- 14/14 line items resolved', delay: 300 },
  { timestamp: '14:22:04.059', level: 'INFO', message: 'Extracting metadata: PackingList_MANIFEST_7G.xlsx', delay: 380 },
  { timestamp: '14:22:04.440', level: 'INFO', message: 'Cargo weight delta check: declared 18,440 kg vs manifest 18,440 kg', delay: 420 },
  { timestamp: '14:22:04.862', level: 'OK', message: 'Packing list quantity matched -- zero discrepancy', delay: 250 },
  { timestamp: '14:22:05.115', level: 'INFO', message: 'Dispatching to distributed hash oracle -- 14 active nodes', delay: 700 },
  { timestamp: '14:22:05.818', level: 'INFO', message: 'Node consensus: 14/14 responded within SLA threshold', delay: 400 },
  { timestamp: '14:22:06.221', level: 'HASH', message: 'Merkle root: 8E3B-A92C-44F1-9920-BC34-DE01-FC99-8821-44B0-C221', delay: 300 },
  { timestamp: '14:22:06.524', level: 'INFO', message: 'Cross-referencing Baltic corridor compliance registry', delay: 450 },
  { timestamp: '14:22:06.977', level: 'OK', message: 'All documents: cryptographic fingerprints matched', delay: 300 },
  { timestamp: '14:22:07.280', level: 'SYSTEM', message: 'Verification complete -- generating certificate payload', delay: 500 },
  { timestamp: '14:22:07.783', level: 'OK', message: '>>> AUDIT PASSED -- redirecting to results', delay: 800 },
]

const levelColor: Record<LogLevel, string> = {
  OK: 'text-emerald-400',
  WARN: 'text-amber-400',
  HASH: 'text-[#e90716]',
  SYSTEM: 'text-white/60',
  INFO: 'text-sky-400/70',
}

export const ProcessingScreen: React.FC<ReadonlyProcessingScreenProps> = ({ onComplete }) => {
  const [visibleLines, setVisibleLines] = useState<LogLine[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [phase, setPhase] = useState<'running' | 'complete'>('running')
  const [cursorBlink, setCursorBlink] = useState(true)

  const terminalRef = useRef<HTMLDivElement | null>(null)

  const progressPct = useMemo(() => (currentIndex / LOG_LINES.length) * 100, [currentIndex])

  useEffect(() => {
    const cursorInterval = window.setInterval(() => {
      setCursorBlink((prev) => !prev)
    }, 530)

    return () => window.clearInterval(cursorInterval)
  }, [])

  useEffect(() => {
    if (currentIndex >= LOG_LINES.length) {
      setPhase('complete')
      const completeTimer = window.setTimeout(() => {
        onComplete()
      }, 1200)

      return () => window.clearTimeout(completeTimer)
    }

    const line = LOG_LINES[currentIndex]
    const timer = window.setTimeout(() => {
      setVisibleLines((prev) => [...prev, line])
      setCurrentIndex((prev) => prev + 1)
    }, line.delay)

    return () => window.clearTimeout(timer)
  }, [currentIndex, onComplete])

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
          <span className="ml-3 font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">session cp-992-x :: clearpath verification</span>
        </div>

        <div
          ref={terminalRef}
          className="h-[420px] overflow-y-auto px-5 py-4 font-mono text-sm leading-relaxed [&::-webkit-scrollbar-thumb]:bg-secondary/40 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar]:w-1.5"
        >
          {visibleLines.map((line, index) => (
            <div key={`${line.timestamp}-${index}`} className="animate-log-line whitespace-pre-wrap break-words">
              <span className="text-white/25">{line.timestamp}</span>{' '}
              <span className={levelColor[line.level]}>[{line.level}]</span>{' '}
              <span className="text-[#c8c8d8]">{line.message}</span>
            </div>
          ))}

          {phase === 'running' ? (
            <div className="mt-1 flex items-center gap-2">
              <span className="text-white/35">{`[${currentIndex >= LOG_LINES.length ? 'OK' : 'SYSTEM'}]`}</span>
              <span className="text-white/50">awaiting input</span>
              <span className={`h-4 w-2 bg-secondary transition-opacity ${cursorBlink ? 'opacity-100' : 'opacity-20'}`} />
            </div>
          ) : null}
        </div>

        <div className="border-t border-white/10 px-5 py-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.15em] text-white/55">
            Processing {Math.min(currentIndex, LOG_LINES.length)}/{LOG_LINES.length} operations...
          </div>
          <div className="h-1.5 w-full bg-white/10">
            <div className="h-full bg-secondary transition-all duration-300" style={{ width: `${progressPct}%` }} />
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

