import { useState } from 'react'
import { ClearPathScreen } from './components/ClearPathScreen'
import { VerificationResultsScreen } from './components/VerificationResultsScreen'

function App() {
  const [currentScreen, setCurrentScreen] = useState<'home' | 'results'>('home');

  return (
    <>
      {currentScreen === 'home' ? (
        <ClearPathScreen onNavigateToResults={() => setCurrentScreen('results')} />
      ) : (
        <VerificationResultsScreen onNavigateHome={() => setCurrentScreen('home')} />
      )}
    </>
  )
}

export default App
