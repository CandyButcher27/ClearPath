import { useState } from 'react'
import { ClearPathScreen } from './components/ClearPathScreen'
import { ProcessingScreen } from './components/ProcessingScreen'
import { VerificationResultsScreen } from './components/VerificationResultsScreen'

function App() {
  const [currentScreen, setCurrentScreen] = useState<'home' | 'processing' | 'results'>('home')

  if (currentScreen === 'home') {
    return <ClearPathScreen onSubmit={() => setCurrentScreen('processing')} />
  }

  if (currentScreen === 'processing') {
    return <ProcessingScreen onComplete={() => setCurrentScreen('results')} />
  }

  return <VerificationResultsScreen onNavigateHome={() => setCurrentScreen('home')} />
}

export default App
