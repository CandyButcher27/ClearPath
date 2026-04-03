import React from 'react'
import { verificationResultsData } from '../data/mockData'
import { useScrollAnimation } from '../hooks/useScrollAnimation'

export interface ReadonlyVerificationResultsScreenProps {
  onNavigateHome: () => void
}

export const VerificationResultsScreen: React.FC<ReadonlyVerificationResultsScreenProps> = ({ onNavigateHome }) => {
  const scrollY = useScrollAnimation()

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
              <span className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-secondary">Process ID: {verificationResultsData.header.processId}</span>
              <h1 className="text-7xl font-black uppercase leading-[0.9] tracking-tighter text-primary md:text-8xl">{verificationResultsData.header.title}</h1>
            </div>
          </div>
          <p className="mt-4 max-w-2xl border-l-4 border-secondary pl-6 text-lg leading-relaxed text-on-surface-variant">
            {verificationResultsData.header.description}
          </p>
        </header>

        <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-12">
          <div className="stagger-children lg:col-span-8 space-y-4">
            {verificationResultsData.points.map((point, index) => (
              <div
                key={point.id}
                className={`reveal point-${index} group rounded-sm border-l-8 border-primary bg-surface-container-lowest p-8 shadow-sm transition-all duration-500 hover:bg-surface-container hover:shadow-xl`}
                style={{ transform: `translateY(${index % 2 === 0 ? scrollY * 0.02 : scrollY * -0.015}px)` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant">Metadata Point {point.id}</span>
                    <h3 className="text-2xl font-bold tracking-tight text-primary">{point.title}</h3>
                  </div>
                  <img
                    src="/ccircle.png"
                    alt="verified"
                    className="animated-check inline-block"
                    style={{ width: '32px', height: '32px', objectFit: 'contain', animationDelay: `${0.1 + index * 0.1}s` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="scroll-reveal-left lg:col-span-4 sticky top-32 space-y-8">
            <div className="group relative overflow-hidden rounded-sm border border-white/8 bg-surface-container-high p-8 shadow-xl">
              <div className="absolute inset-0 bg-gradient-to-br from-surface-container-high via-surface-container-high to-secondary/10 opacity-50" />
              <div className="relative z-10">
                <h4 className="mb-6 text-[10px] font-bold uppercase tracking-[0.3em] text-on-surface-variant">Final Hash Signature</h4>
                <div className="break-all font-mono text-sm leading-relaxed tracking-wider text-on-surface opacity-90">
                  {verificationResultsData.sidebar.hash}
                </div>

                <div className="mt-8 border-t border-white/10 pt-8">
                  <div className="mb-2 flex justify-between">
                    <span className="text-[10px] font-bold uppercase text-on-surface-variant">Verified At</span>
                    <span className="text-xs font-bold text-on-surface">{verificationResultsData.sidebar.verifiedAt}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[10px] font-bold uppercase text-on-surface-variant">Nodes Checked</span>
                    <span className="text-xs font-bold text-secondary">{verificationResultsData.sidebar.nodesChecked}</span>
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

            <button className="btn-glow relative w-full overflow-hidden rounded-sm bg-secondary py-5 text-sm font-black uppercase tracking-[0.2em] text-white shadow-[0_0_15px_rgba(227,30,36,0.2)] transition-all hover:bg-[#f12a31] hover:shadow-[0_0_30px_rgba(227,30,36,0.5)] active:scale-[0.98]">
              Generate Final Certificate
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
