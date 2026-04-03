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