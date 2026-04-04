import React, { useState, useEffect, useRef } from 'react'
import { ClearPathScreen } from './components/ClearPathScreen'
import { ProcessingScreen } from './components/ProcessingScreen'
import { VerificationResultsScreen } from './components/VerificationResultsScreen'

export interface UploadedFiles {
  bill_of_lading: File | null
  invoice: File | null
  packing_list: File | null
}

export interface ApiResult {
  success: boolean
  session_id: string
  normalized: Record<string, unknown>
  raw_shipment: Record<string, unknown>
  telemetry?: {
    timing?: { total_duration_ms?: number }
    extraction?: {
      chars_extracted?: number
      chars_sent?: number
      coverage_ratio?: number
      parse_retries?: number
      fallback_used?: boolean
    }
    kpis?: {
      risk_score?: number
      checks_passed?: number
      total_checks?: number
      estimated_time_saved_minutes?: number
      completeness_index?: number
    }
  }
  explainability?: {
    items?: Array<{
      id?: string
      category?: string
      flag_name?: string
      is_flagged?: boolean
      severity?: string
      confidence?: number
      rule?: string
      threshold?: string
      source_fields?: string[]
      evidence?: Array<{ path?: string; value?: unknown }>
    }>
    summary?: {
      total_checks?: number
      flagged_checks?: number
      completeness_index?: number
    }
  }
}

function FadeScreen({ children, screenKey }: { children: React.ReactNode; screenKey: string }) {
  const [visible, setVisible] = useState(false)
  const prevKey = useRef(screenKey)

  useEffect(() => {
    prevKey.current = screenKey
    const t = setTimeout(() => setVisible(true), 30)
    return () => {
      clearTimeout(t)
      setVisible(false)
    }
  }, [screenKey])

  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
        transition: 'opacity 0.35s ease, transform 0.35s ease',
      }}
    >
      {children}
    </div>
  )
}

function App() {
  const [currentScreen, setCurrentScreen] = useState<'home' | 'processing' | 'results'>('home')
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFiles>({
    bill_of_lading: null,
    invoice: null,
    packing_list: null,
  })
  const [apiResult, setApiResult] = useState<ApiResult | null>(null)

  if (currentScreen === 'home') {
    return (
      <FadeScreen screenKey="home">
        <ClearPathScreen
          onSubmit={(files) => {
            setUploadedFiles(files)
            setCurrentScreen('processing')
          }}
        />
      </FadeScreen>
    )
  }

  if (currentScreen === 'processing') {
    return (
      <FadeScreen screenKey="processing">
        <ProcessingScreen
          files={uploadedFiles}
          onComplete={(result) => {
            setApiResult(result)
            setCurrentScreen('results')
          }}
          onError={() => setCurrentScreen('home')}
          onCancel={() => setCurrentScreen('home')}
        />
      </FadeScreen>
    )
  }

  return (
    <FadeScreen screenKey="results">
      <VerificationResultsScreen
        result={apiResult}
        onNavigateHome={() => {
          setCurrentScreen('home')
          setApiResult(null)
        }}
      />
    </FadeScreen>
  )
}

export default App
