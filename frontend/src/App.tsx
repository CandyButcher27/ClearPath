import { useState } from 'react'
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
      <ClearPathScreen
        onSubmit={(files) => {
          setUploadedFiles(files)
          setCurrentScreen('processing')
        }}
      />
    )
  }

  if (currentScreen === 'processing') {
    return (
      <ProcessingScreen
        files={uploadedFiles}
        onComplete={(result) => {
          setApiResult(result)
          setCurrentScreen('results')
        }}
        onError={() => setCurrentScreen('home')}
      />
    )
  }

  return (
    <VerificationResultsScreen
      result={apiResult}
      onNavigateHome={() => {
        setCurrentScreen('home')
        setApiResult(null)
      }}
    />
  )
}

export default App
