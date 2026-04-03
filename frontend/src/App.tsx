import { useState } from 'react'
import { ClearPathScreen } from './components/ClearPathScreen'
import { ProcessingScreen } from './components/ProcessingScreen'
import { VerificationResultsScreen } from './components/VerificationResultsScreen'
import type { VerificationResults } from './types/api'

function App() {
  const [currentScreen, setCurrentScreen] = useState<'home' | 'processing' | 'results'>('home')
  const [jobId, setJobId] = useState<string | null>(null)
  const [results, setResults] = useState<VerificationResults | null>(null)

  if (currentScreen === 'home') {
    return (
      <ClearPathScreen
        onSubmit={(id: string) => {
          setJobId(id)
          setCurrentScreen('processing')
        }}
      />
    )
  }

  if (currentScreen === 'processing') {
    return (
      <ProcessingScreen
        jobId={jobId!}
        onComplete={(r: VerificationResults | null) => {
          setResults(r)
          setCurrentScreen('results')
        }}
      />
    )
  }

  return (
    <VerificationResultsScreen
      results={results}
      jobId={jobId!}
      onNavigateHome={() => {
        setCurrentScreen('home')
        setJobId(null)
        setResults(null)
      }}
    />
  )
}

export default App
