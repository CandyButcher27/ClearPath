import React, { useEffect, useState } from 'react'
import { clearPathData } from '../data/mockData'
import { useScrollAnimation } from '../hooks/useScrollAnimation'

export interface ReadonlyClearPathScreenProps {
  onSubmit: () => void
}

export const ClearPathScreen: React.FC<ReadonlyClearPathScreenProps> = ({ onSubmit }) => {
  const scrollY = useScrollAnimation()
  const [gridPos, setGridPos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = e.clientX / window.innerWidth
      const y = e.clientY / window.innerHeight
      setGridPos({ x: x * 20, y: y * 20 })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <div className="min-h-screen overflow-x-hidden bg-surface text-on-surface selection:bg-secondary/30">
      <div className="wireframe-container pointer-events-none fixed top-1/2 -right-12 z-40 hidden xl:block">
        <div
          className="wireframe-cube"
          style={{ transform: `rotateX(${scrollY * 0.1}deg) rotateY(${scrollY * 0.15}deg)` }}
        >
          <div className="cube-face front" />
          <div className="cube-face back" />
          <div className="cube-face right" />
          <div className="cube-face left" />
          <div className="cube-face top" />
          <div className="cube-face bottom" />
        </div>
      </div>

      <div
        className="fixed inset-0 z-0 grid-overlay opacity-50 transition-transform duration-100 ease-out pointer-events-none"
        style={{ transform: `translate(${gridPos.x}px, ${gridPos.y}px)` }}
      />

      <nav className="fixed top-0 z-50 w-full border-b border-outline-variant/20 bg-surface/80 shadow-[0_1px_0_rgba(255,255,255,0.04),0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-[1440px] items-center justify-between px-8">
          <div className="logo-glow text-2xl font-black uppercase tracking-tighter text-primary">VERIFY_LOGIC</div>
          <div className="hidden items-center gap-10 md:flex">
            <a className="border-b-2 border-on-surface pb-1 font-inter text-xs font-extrabold uppercase tracking-tighter text-primary" href="#docs">Documents</a>
            <a className="font-inter text-xs font-extrabold uppercase tracking-tighter text-on-surface-variant transition-colors hover:text-primary" href="#verify">Verification</a>
            <a className="font-inter text-xs font-extrabold uppercase tracking-tighter text-on-surface-variant transition-colors hover:text-primary" href="#logs">Audit Logs</a>
            <a className="font-inter text-xs font-extrabold uppercase tracking-tighter text-on-surface-variant transition-colors hover:text-primary" href="#compliance">Compliance</a>
          </div>
          <div className="flex items-center gap-6">
            <button className="font-inter text-xs font-extrabold uppercase tracking-tighter text-on-surface-variant transition-colors hover:text-primary">System Status</button>
            <button className="bg-primary px-8 py-3 font-inter text-xs font-extrabold uppercase tracking-tighter text-on-primary transition-all duration-300 hover:bg-secondary">Secure Login</button>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 h-[2px] w-16 bg-secondary" />
      </nav>

      <main className="pt-20">
        <section className="relative flex min-h-[80vh] items-center overflow-hidden bg-surface">
          <div className="hero-glow" />
          <div className="relative z-10 mx-auto grid w-full max-w-[1440px] items-center gap-16 px-8 py-24 lg:grid-cols-2">
            <div className="animate-fade-up">
              <div className="mb-10 inline-flex items-center gap-2 bg-surface-container-high px-3 py-1">
                <span className="relative flex h-2 w-2">
                  <span className="animate-status-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary" />
                </span>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-on-surface-variant">{clearPathData.hero.badge}</span>
              </div>
              <h1 className="mb-10 text-7xl font-black leading-[0.85] tracking-tighter text-primary md:text-9xl">
                {clearPathData.hero.title[0]}
                <br />
                <span className="text-red-600">{clearPathData.hero.title[1]}</span>.
              </h1>
              <p className="mb-12 max-w-lg text-xl font-bold uppercase leading-tight tracking-tight text-on-surface-variant">
                {clearPathData.hero.description}
              </p>
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={onSubmit}
                  className="group relative flex items-center gap-4 overflow-hidden bg-red-600 px-10 py-5 text-xs font-black uppercase tracking-widest text-white transition-all duration-500 hover:bg-primary"
                >
                  <span className="relative z-10 flex items-center gap-4">
                    Initiate Audit
                    <img src="/arrow.webp" alt="arrow" className="inline-block h-4 w-4 object-contain transition-transform group-hover:translate-x-1" />
                  </span>
                </button>
                <button className="border-2 border-on-surface/30 px-10 py-5 text-xs font-black uppercase tracking-widest transition-all duration-500 hover:border-on-surface hover:bg-on-surface hover:text-surface">
                  API Specs
                </button>
              </div>
            </div>

            <div className="hero-parallax reveal-delay-2 relative flex h-[600px] w-full animate-fade-up items-center justify-center overflow-hidden">
              <img
                alt="Modern Cargo Ship"
                className="h-full w-full object-contain grayscale-0 contrast-110"
                src={clearPathData.hero.heroImage}
                style={{ transform: `translate(${scrollY * 0.2}px, ${scrollY * 0.1}px) scale(1.05)` }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-surface via-transparent to-transparent pointer-events-none" />

              <div className="animate-float absolute bottom-10 left-10 max-w-sm border-l-8 border-secondary bg-surface-container p-8 shadow-2xl backdrop-blur-sm">
                <div className="mb-3 flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-status-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary" />
                  </span>
                  <span className="block text-[11px] font-black uppercase tracking-widest text-secondary">Live Status</span>
                </div>
                <p className="text-sm font-black uppercase leading-tight tracking-tight text-primary">
                  {clearPathData.hero.statusText}
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden bg-surface-container-highest py-32">
          <div className="relative z-10 mx-auto max-w-[1440px] px-8">
            <div className="scroll-reveal mb-20">
              <h2 className="text-5xl font-black uppercase leading-none tracking-tighter text-primary">Direct ingestion</h2>
              <div className="reveal-line scroll-reveal mt-6" />
              <p className="mt-8 text-xs font-black uppercase tracking-widest text-on-surface-variant">Deploy your documents into the verification pipeline.</p>
            </div>

            <div className="stagger-children grid gap-8 md:grid-cols-3">
              {clearPathData.documents.map((doc, idx) => (
                <div
                  key={doc.title}
                  className={`scroll-reveal group relative border border-white/5 bg-surface-container/60 p-12 backdrop-blur-sm transition-all duration-500 hover:border-secondary/30 hover:shadow-[0_0_0_1px_rgba(233,7,22,0.12),0_20px_60px_rgba(0,0,0,0.3)] ${idx > 0 ? `reveal-delay-${idx}` : ''}`}
                >
                  <img
                    src="/circle.png"
                    alt="verified"
                    className="animated-check absolute right-4 top-4 inline-block h-6 w-6 object-contain"
                    style={{ animationDelay: `${0.1 + idx * 0.1}s` }}
                  />
                  <div className="mb-10 h-12 w-12">
                    <img src={doc.icon} alt={doc.title} className="h-full w-full object-contain" />
                  </div>
                  <h3 className="mb-4 text-2xl font-black uppercase tracking-tighter text-primary">{doc.title}</h3>
                  <p className="mb-10 text-xs font-bold uppercase leading-relaxed tracking-tight text-on-surface-variant">{doc.description}</p>

                  <div className="flex h-40 w-full flex-col items-center justify-center border border-dashed border-white/10 transition-all duration-500 group-hover:border-secondary/30 group-hover:bg-secondary/5">
                    <span className="material-symbols-outlined mb-2 text-on-surface-variant transition-colors group-hover:text-secondary">upload_file</span>
                    <span className="text-[10px] font-black uppercase tracking-widest text-on-surface-variant transition-colors group-hover:text-secondary">Drag &amp; Drop</span>
                  </div>
                  <button className="mt-6 w-full bg-primary py-4 text-[10px] font-black uppercase tracking-widest text-on-primary transition-colors duration-300 hover:bg-secondary">Upload File</button>
                </div>
              ))}
            </div>

            <div className="scroll-reveal mt-20 flex justify-center">
              <button onClick={onSubmit} className="animate-pulse-accent flex items-center gap-5 bg-red-600 px-16 py-6 text-sm font-black uppercase tracking-[0.3em] text-white transition-all duration-300 hover:bg-red-700">
                Submit for Verification
              </button>
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden bg-surface-container-lowest py-32">
          <div className="relative z-10 mx-auto grid max-w-[1440px] items-end gap-16 px-8 lg:grid-cols-4">
            <div className="scroll-reveal-left lg:col-span-2">
              <h2 className="mb-8 text-6xl font-black uppercase leading-[0.9] tracking-tighter text-primary">
                Architects of
                <br />
                Global Trade.
              </h2>
              <p className="max-w-md text-xs font-black uppercase leading-relaxed tracking-widest text-on-surface-variant">
                Our infrastructure processes over 4.2 million logistics documents monthly with a verified accuracy rate of 99.98%.
              </p>
            </div>
            {clearPathData.stats.map((stat, idx) => (
              <div key={stat.label} className={`scroll-reveal flex flex-col border-l-4 ${idx % 2 === 0 ? 'border-secondary' : 'border-primary'} pb-2 pl-10 reveal-delay-${idx + 1}`}>
                <span className="scroll-reveal-scale text-6xl font-black tracking-tighter text-primary">{stat.value}</span>
                <span className="mt-2 text-[11px] font-black uppercase tracking-widest text-on-surface-variant">{stat.label}</span>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="relative overflow-hidden bg-black py-20 text-white">
        <div className="relative z-10 mx-auto max-w-[1440px] px-8">
          <div className="flex flex-col items-start justify-between gap-12 md:flex-row md:items-center">
            <div className="text-3xl font-black uppercase tracking-tighter">VERIFY_LOGIC</div>
            <div className="grid grid-cols-2 gap-x-12 gap-y-6 md:flex">
              <a className="font-inter text-[10px] font-black uppercase tracking-widest text-zinc-500 transition-colors hover:text-secondary" href="#">Privacy Policy</a>
              <a className="font-inter text-[10px] font-black uppercase tracking-widest text-zinc-500 transition-colors hover:text-secondary" href="#">Terms of Service</a>
              <a className="font-inter text-[10px] font-black uppercase tracking-widest text-zinc-500 transition-colors hover:text-secondary" href="#">Security Whitepaper</a>
              <a className="font-inter text-[10px] font-black uppercase tracking-widest text-zinc-500 transition-colors hover:text-secondary" href="#">API Documentation</a>
            </div>
          </div>
          <div className="mt-20 flex flex-col items-center justify-between gap-6 border-t border-zinc-800 pt-10 md:flex-row">
            <p className="font-inter text-[10px] font-black uppercase tracking-widest text-zinc-600">(c) 2024 Industrial Architect Verification Systems.</p>
            <div className="flex gap-4">
              <div className="flex h-8 w-8 cursor-pointer items-center justify-center bg-zinc-900 transition-colors hover:bg-secondary">
                <span className="material-symbols-outlined text-sm">terminal</span>
              </div>
              <div className="flex h-8 w-8 cursor-pointer items-center justify-center bg-zinc-900 transition-colors hover:bg-secondary">
                <span className="material-symbols-outlined text-sm">hub</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
