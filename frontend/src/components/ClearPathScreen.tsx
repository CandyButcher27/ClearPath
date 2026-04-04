import React, { useEffect, useState } from 'react'
import { clearPathData } from '../data/mockData'
import { useScrollAnimation } from '../hooks/useScrollAnimation'
import type { UploadedFiles } from '../App'

export interface ReadonlyClearPathScreenProps {
  onSubmit: (files: UploadedFiles) => void
}

export const ClearPathScreen: React.FC<ReadonlyClearPathScreenProps> = ({ onSubmit }) => {
  const scrollY = useScrollAnimation()
  const [gridPos, setGridPos] = useState({ x: 0, y: 0 })
  const [files, setFiles] = useState<UploadedFiles>({
    bill_of_lading: null,
    invoice: null,
    packing_list: null,
  })
  const [dragging, setDragging] = useState<keyof UploadedFiles | null>(null)

  const fileKeys: (keyof UploadedFiles)[] = ['bill_of_lading', 'invoice', 'packing_list']
  const allFilesSelected = fileKeys.every((k) => files[k] !== null)

  const handleFileChange = (key: keyof UploadedFiles, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setFiles((prev) => ({ ...prev, [key]: file }))
  }

  const handleDrop = (key: keyof UploadedFiles, e: React.DragEvent) => {
    e.preventDefault()
    setDragging(null)
    const file = e.dataTransfer.files?.[0]
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      setFiles((prev) => ({ ...prev, [key]: file }))
    }
  }

  useEffect(() => {
    let rafId: number | null = null
    const handleMouseMove = (e: MouseEvent) => {
      if (rafId !== null) return
      rafId = requestAnimationFrame(() => {
        const x = e.clientX / window.innerWidth
        const y = e.clientY / window.innerHeight
        setGridPos({ x: x * 20, y: y * 20 })
        rafId = null
      })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      if (rafId !== null) cancelAnimationFrame(rafId)
    }
  }, [])

  return (
    <div className="min-h-screen overflow-x-hidden bg-surface text-on-surface selection:bg-secondary/30">
      <div className="wireframe-container pointer-events-none fixed top-1/2 -right-12 z-40 hidden xl:block">
        <div
          className="wireframe-cube"
          style={{ transform: `rotateX(${scrollY * 0.1}deg) rotateY(${scrollY * 0.15}deg)`, willChange: 'transform' }}
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
          <div className="logo-glow text-2xl font-black uppercase tracking-tighter text-primary">ClearPath</div>
          <div className="flex items-center gap-3">
            <span className="relative flex h-2 w-2">
              <span className="animate-status-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary" />
            </span>
            <span className="font-inter text-[10px] font-black uppercase tracking-[0.2em] text-on-surface-variant">System Online</span>
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
              <p className="text-xs font-black uppercase tracking-widest text-on-surface-variant">
                Upload your documents below to begin verification.
              </p>
            </div>

            <div className="hero-parallax reveal-delay-2 relative flex h-[600px] w-full animate-fade-up items-center justify-center overflow-hidden">
              <img
                alt="Modern Cargo Ship"
                className="h-full w-full object-contain grayscale-0 contrast-110"
                src={clearPathData.hero.heroImage}
                style={{ transform: `translate(${scrollY * 0.2}px, ${scrollY * 0.1}px) scale(1.05)`, willChange: 'transform' }}
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

            <div className="grid gap-6 md:grid-cols-3">
              {clearPathData.documents.map((doc, i) => {
                const keys: (keyof UploadedFiles)[] = ['bill_of_lading', 'invoice', 'packing_list']
                const key = keys[i]
                return (
                  <div key={doc.title} className="border border-outline-variant/20 bg-surface-container-low p-6">
                    <img src={doc.icon} alt={doc.title} className="mb-4 h-10 w-10 object-contain" />
                    <h3 className="mb-2 text-sm font-black uppercase tracking-widest text-primary">{doc.title}</h3>
                    <p className="mb-4 text-xs text-on-surface-variant">{doc.description}</p>
                    <label
                      className={`flex cursor-pointer flex-col items-center gap-2 border border-dashed p-4 text-xs transition-colors ${dragging === key
                        ? 'border-secondary bg-secondary/10 text-secondary'
                        : files[key]
                          ? 'border-secondary/60 text-secondary'
                          : 'border-outline-variant/40 text-on-surface-variant hover:border-secondary hover:text-secondary'
                        }`}
                      onDragOver={(e) => { e.preventDefault(); setDragging(key) }}
                      onDragLeave={() => setDragging(null)}
                      onDrop={(e) => handleDrop(key, e)}
                    >
                      {files[key] ? (
                        <span className="flex items-center gap-1 font-bold">
                          <span className="text-emerald-400">✓</span> {files[key]!.name}
                        </span>
                      ) : dragging === key ? (
                        <span className="font-bold">Drop PDF here</span>
                      ) : (
                        <span>Click or drag PDF here</span>
                      )}
                      <input
                        type="file"
                        accept=".pdf"
                        className="hidden"
                        onChange={(e) => handleFileChange(key, e)}
                      />
                    </label>
                  </div>
                )
              })}
            </div>

            <div className="scroll-reveal mt-20 flex justify-center">
              <button
                onClick={() => allFilesSelected && onSubmit(files)}
                disabled={!allFilesSelected}
                className={`animate-pulse-accent flex items-center gap-5 bg-red-600 px-16 py-6 text-sm font-black uppercase tracking-[0.3em] text-white transition-all duration-300 hover:bg-red-700 ${!allFilesSelected ? 'opacity-40 cursor-not-allowed' : ''}`}
              >
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
                Our infrastructure processes logistics documents monthly with reliable0 accuracy.
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

      <footer className="relative overflow-hidden bg-black py-12 text-white">
        <div className="relative z-10 mx-auto max-w-[1440px] px-8">
          <div className="flex flex-col items-center justify-between gap-4 border-t border-zinc-800 pt-8 md:flex-row">
            <div className="text-xl font-black uppercase tracking-tighter">ClearPath</div>
            <p className="font-inter text-[10px] font-black uppercase tracking-widest text-zinc-600">&copy; {new Date().getFullYear()} ClearPath — Intelligent Shipment Verification.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
