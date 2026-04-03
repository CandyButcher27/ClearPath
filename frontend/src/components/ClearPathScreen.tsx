import React, { useEffect, useState } from 'react';
import { clearPathData } from '../data/mockData';
import { useScrollAnimation } from '../hooks/useScrollAnimation';

export interface ReadonlyClearPathScreenProps {
  onNavigateToResults: () => void;
}

export const ClearPathScreen: React.FC<ReadonlyClearPathScreenProps> = ({ onNavigateToResults }) => {
  const scrollY = useScrollAnimation();
  const [gridPos, setGridPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = e.clientX / window.innerWidth;
      const y = e.clientY / window.innerHeight;
      setGridPos({ x: x * 20, y: y * 20 });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="bg-surface text-on-surface selection:bg-secondary/30 overflow-x-hidden min-h-screen">
      {/* Floating 3D Component */}
      <div className="fixed top-1/2 -right-12 z-40 hidden xl:block pointer-events-none wireframe-container">
        <div
          className="wireframe-cube"
          style={{ transform: `rotateX(${scrollY * 0.1}deg) rotateY(${scrollY * 0.15}deg)` }}
        >
          <div className="cube-face front"></div>
          <div className="cube-face back"></div>
          <div className="cube-face right"></div>
          <div className="cube-face left"></div>
          <div className="cube-face top"></div>
          <div className="cube-face bottom"></div>
        </div>
      </div>

      {/* Grid Overlay */}
      <div
        className="fixed inset-0 grid-overlay pointer-events-none z-0 opacity-50 transition-transform duration-100 ease-out"
        style={{ transform: `translate(${gridPos.x}px, ${gridPos.y}px)` }}
      ></div>

      {/* Top Navigation Bar */}
      <nav className="fixed top-0 w-full z-50 bg-white/90 backdrop-blur-xl border-b border-zinc-200">
        <div className="flex justify-between items-center px-8 h-20 max-w-[1440px] mx-auto">
          <div className="text-2xl font-black tracking-tighter text-black uppercase">VERIFY_LOGIC</div>
          <div className="hidden md:flex gap-10 items-center">
            <a className="font-inter tracking-tighter font-extrabold text-xs uppercase text-black border-b-2 border-black pb-1" href="#docs">Documents</a>
            <a className="font-inter tracking-tighter font-extrabold text-xs uppercase text-zinc-400 hover:text-black transition-colors" href="#verify">Verification</a>
            <a className="font-inter tracking-tighter font-extrabold text-xs uppercase text-zinc-400 hover:text-black transition-colors" href="#logs">Audit Logs</a>
            <a className="font-inter tracking-tighter font-extrabold text-xs uppercase text-zinc-400 hover:text-black transition-colors" href="#compliance">Compliance</a>
          </div>
          <div className="flex gap-6 items-center">
            <button className="font-inter tracking-tighter font-extrabold text-xs uppercase text-zinc-400 hover:text-black transition-colors">System Status</button>
            <button className="bg-primary text-on-primary px-8 py-3 font-inter tracking-tighter font-extrabold text-xs uppercase hover:bg-secondary transition-all duration-300">Secure Login</button>
          </div>
        </div>
      </nav>

      <main className="pt-20">
        {/* Hero Section */}
        <section className="relative min-h-[80vh] flex items-center overflow-hidden bg-surface">
          <div className="max-w-[1440px] mx-auto px-8 w-full grid lg:grid-cols-2 gap-16 items-center py-24 relative z-10">
            <div className="animate-fade-up">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-surface-container-high mb-10">
                <span className="relative flex h-2 w-2">
                  <span className="animate-status-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
                </span>
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-on-surface-variant">{clearPathData.hero.badge}</span>
              </div>
              <h1 className="text-7xl md:text-9xl font-black tracking-tighter leading-[0.85] text-primary mb-10">
                {clearPathData.hero.title[0]}<br />
                <span className="text-red-600">{clearPathData.hero.title[1]}</span>.
              </h1>
              <p className="text-xl text-on-surface-variant max-w-lg font-bold leading-tight mb-12 uppercase tracking-tight">
                {clearPathData.hero.description}
              </p>
              <div className="flex flex-wrap gap-4">
                <button
                  onClick={onNavigateToResults}
                  className="bg-red-600 text-white px-10 py-5 font-black uppercase tracking-widest text-xs flex items-center gap-4 hover:bg-primary transition-all duration-500 group relative overflow-hidden"
                >
                  <span className="relative z-10 flex items-center gap-4">
                    Initiate Audit
                    <img src="/arrow.webp" alt="arrow" className="w-4 h-4 inline-block group-hover:translate-x-1 transition-transform object-contain" />
                  </span>
                </button>
                <button className="border-2 border-black px-10 py-5 font-black uppercase tracking-widest text-xs hover:bg-black hover:text-white transition-all duration-500">
                  API Specs
                </button>
              </div>
            </div>
            <div className="relative h-[600px] w-full overflow-hidden animate-fade-up hero-parallax flex items-center justify-center reveal-delay-2">
              <img
                alt="Modern Cargo Ship"
                className="w-full h-full object-contain grayscale-0 contrast-110"
                src={clearPathData.hero.heroImage}
                style={{ transform: `translate(${scrollY * 0.2}px, ${scrollY * 0.1}px) scale(1.05)` }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent pointer-events-none"></div>

              {/* Status Pulse Indicator */}
              <div className="absolute bottom-10 left-10 p-8 bg-white border-l-8 border-secondary max-w-sm shadow-2xl animate-float">
                <div className="flex items-center gap-2 mb-3">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-status-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
                  </span>
                  <span className="block text-[11px] font-black uppercase tracking-widest text-secondary">Live Status</span>
                </div>
                <p className="text-sm font-black text-primary leading-tight uppercase tracking-tight">
                  {clearPathData.hero.statusText}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Document Upload Grid */}
        <section className="bg-surface-container-highest py-32 relative overflow-hidden">
          <div className="max-w-[1440px] mx-auto px-8 relative z-10">
            <div className="mb-20 scroll-reveal">
              <h2 className="text-5xl font-black tracking-tighter text-primary uppercase leading-none">Direct ingestion</h2>
              <div className="h-1.5 w-24 bg-secondary mt-6"></div>
              <p className="text-xs font-black uppercase tracking-widest text-on-surface-variant mt-8">Deploy your documents into the verification pipeline.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {clearPathData.documents.map((doc, idx) => (
                <div key={idx} className={`scroll-reveal ${idx > 0 ? `reveal-delay-${idx}` : ''} group relative bg-white p-12 border border-zinc-100 hover:shadow-xl transition-all duration-500`}>
                  <div className="mb-10 w-12 h-12">
                    <img src={doc.icon} alt={doc.title} className="w-full h-full object-contain" />
                  </div>
                  <h3 className="text-2xl font-black uppercase tracking-tighter text-primary mb-4">{doc.title}</h3>
                  <p className="text-xs font-bold text-on-surface-variant mb-10 leading-relaxed uppercase tracking-tight">{doc.description}</p>

                  <div className="w-full h-40 border-2 border-dashed border-zinc-200 flex flex-col items-center justify-center group-hover:border-secondary transition-colors duration-500">
                    <span className="material-symbols-outlined text-zinc-300 mb-2 group-hover:text-secondary transition-colors">upload_file</span>
                    <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400 group-hover:text-secondary transition-colors">Drag &amp; Drop</span>
                  </div>
                  <button className="mt-6 w-full bg-black text-white py-4 font-black uppercase tracking-widest text-[10px] hover:bg-secondary transition-colors duration-300">Upload File</button>
                </div>
              ))}
            </div>

            <div className="mt-20 flex justify-center scroll-reveal">
              <button onClick={onNavigateToResults} className="bg-red-600 text-white px-16 py-6 font-black uppercase tracking-[0.3em] text-sm flex items-center gap-5 hover:bg-red-700 transition-all duration-300 animate-pulse-accent">
                Submit for Verification
              </button>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-32 bg-white relative overflow-hidden">
          <div className="max-w-[1440px] mx-auto px-8 grid lg:grid-cols-4 gap-16 items-end relative z-10">
            <div className="lg:col-span-2 scroll-reveal">
              <h2 className="text-6xl font-black tracking-tighter text-primary leading-[0.9] uppercase mb-8">Architects of<br />Global Trade.</h2>
              <p className="text-on-surface-variant text-xs font-black uppercase tracking-widest leading-relaxed max-w-md">
                Our infrastructure processes over 4.2 million logistics documents monthly with a verified accuracy rate of 99.98%.
              </p>
            </div>
            {clearPathData.stats.map((stat, idx) => (
              <div key={idx} className={`flex flex-col pb-2 border-l-4 border-${idx % 2 === 0 ? 'secondary' : 'black'} pl-10 scroll-reveal reveal-delay-${idx + 1}`}>
                <span className="text-6xl font-black text-primary tracking-tighter">{stat.value}</span>
                <span className="text-[11px] font-black uppercase tracking-widest text-on-surface-variant mt-2">{stat.label}</span>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="bg-black text-white py-20 relative overflow-hidden">
        <div className="max-w-[1440px] mx-auto px-8 relative z-10">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-12">
            <div className="text-3xl font-black tracking-tighter uppercase">VERIFY_LOGIC</div>
            <div className="grid grid-cols-2 md:flex gap-x-12 gap-y-6">
              <a className="font-inter text-[10px] tracking-widest uppercase font-black text-zinc-500 hover:text-secondary transition-colors" href="#">Privacy Policy</a>
              <a className="font-inter text-[10px] tracking-widest uppercase font-black text-zinc-500 hover:text-secondary transition-colors" href="#">Terms of Service</a>
              <a className="font-inter text-[10px] tracking-widest uppercase font-black text-zinc-500 hover:text-secondary transition-colors" href="#">Security Whitepaper</a>
              <a className="font-inter text-[10px] tracking-widest uppercase font-black text-zinc-500 hover:text-secondary transition-colors" href="#">API Documentation</a>
            </div>
          </div>
          <div className="mt-20 pt-10 border-t border-zinc-800 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="font-inter text-[10px] tracking-widest uppercase font-black text-zinc-600">
              © 2024 Industrial Architect Verification Systems.
            </p>
            <div className="flex gap-4">
              <div className="w-8 h-8 bg-zinc-900 flex items-center justify-center hover:bg-secondary transition-colors cursor-pointer">
                <span className="material-symbols-outlined text-sm">terminal</span>
              </div>
              <div className="w-8 h-8 bg-zinc-900 flex items-center justify-center hover:bg-secondary transition-colors cursor-pointer">
                <span className="material-symbols-outlined text-sm">hub</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
