import React from 'react';
import { verificationResultsData } from '../data/mockData';
import { useScrollAnimation } from '../hooks/useScrollAnimation';

export interface ReadonlyVerificationResultsScreenProps {
  onNavigateHome: () => void;
}

export const VerificationResultsScreen: React.FC<ReadonlyVerificationResultsScreenProps> = ({ onNavigateHome }) => {
  const scrollY = useScrollAnimation();

  return (
    <div className="bg-surface text-on-surface selection:bg-secondary/20 min-h-screen">
      {/* Decorative Grid Overlay */}
      <div className="fixed inset-0 grid-bg pointer-events-none z-0"></div>

      {/* Floating Wireframe Decor */}
      <div
        className="fixed top-40 right-10 z-0 opacity-20 hidden lg:block wireframe-cube pointer-events-none"
      >
        <div
          className="cube-inner"
          style={{ transform: `rotateX(${45 + scrollY * 0.15}deg) rotateY(${45 + scrollY * 0.075}deg) rotateZ(${scrollY * 0.03}deg)` }}
        >
          <div className="cube-face" style={{ transform: 'translateZ(30px)' }}></div>
          <div className="cube-face" style={{ transform: 'rotateY(90deg) translateZ(30px)' }}></div>
          <div className="cube-face" style={{ transform: 'rotateY(180deg) translateZ(30px)' }}></div>
          <div className="cube-face" style={{ transform: 'rotateY(-90deg) translateZ(30px)' }}></div>
          <div className="cube-face" style={{ transform: 'rotateX(90deg) translateZ(30px)' }}></div>
          <div className="cube-face" style={{ transform: 'rotateX(-90deg) translateZ(30px)' }}></div>
        </div>
      </div>

      {/* TopNavBar */}
      <nav className="fixed top-0 w-full z-50 bg-white/90 backdrop-blur-md flex justify-between items-center px-8 h-20 border-b border-outline-variant/20">
        <div
          className="text-2xl font-black tracking-tighter text-primary uppercase flex items-center gap-2 cursor-pointer"
          onClick={onNavigateHome}
        >
          <span className="w-8 h-8 bg-secondary flex items-center justify-center text-white text-xl">C</span>
          Clear Path
        </div>
        <div className="hidden md:flex items-center gap-8">
          <a className="text-zinc-500 font-medium hover:text-primary transition-colors" href="#dash">Dashboard</a>
          <a className="text-zinc-500 font-medium hover:text-primary transition-colors" href="#docs">Documents</a>
          <a className="text-zinc-500 font-medium hover:text-primary transition-colors" href="#arch">Archives</a>
          <a className="text-primary border-b-2 border-secondary pb-1 font-inter tracking-tight font-bold" href="#reports">Reports</a>
        </div>
        <div className="flex items-center gap-6">
          <button onClick={onNavigateHome} className="bg-primary text-white px-6 py-2.5 text-sm font-bold tracking-tight rounded-sm hover:bg-opacity-90 transition-all">Verify New</button>
          <div className="w-10 h-10 bg-zinc-200 overflow-hidden rounded-full border-2 border-outline-variant/30">
            <img alt="User profile" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDh5xeDcwyCusmEDNp63h1VQZUFxeavqHnjNiaZeWOyMtq5y_ziSWoKIwB6GKQnnnXincMgsK1tuGmSp9YdIfgf23_L-H-TMuhHMqf7EIKvi3orBUz4_ooZV4ejNIFYcYGv4DV0cvO2FiBG_lO2ANEmHfZ1qnbXSA11UYNpmAzsYGpLqODVjK5NKHM5Jx17hG6hj42gzG8b3OE7U6N4vKmjg_ILOY_HAzQeU5VKzxm2s3qgmrrpl-bcpd6gFpjzF_xNbC6oaHj-GejM" />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 pt-32 pb-24 px-8 max-w-7xl mx-auto">
        {/* Hero Section */}
        <header className="mb-20 animate-fade-up" style={{ transform: `translateY(${scrollY * 0.05}px)` }}>
          <div className="flex items-start gap-4 mb-6">
            <div className="bg-secondary p-1.5 rounded-sm shadow-lg shadow-secondary/20">
              <img src="/circle.png" alt="check circle" className="w-8 h-8 inline-block object-contain" />

            </div>
            <div className="flex flex-col">
              <span className="text-secondary font-bold tracking-[0.2em] text-[10px] uppercase mb-2">Process ID: {verificationResultsData.header.processId}</span>
              <h1 className="text-7xl md:text-8xl font-black tracking-tighter text-primary leading-[0.9] uppercase">{verificationResultsData.header.title}</h1>
            </div>
          </div>
          <p className="text-on-surface-variant max-w-2xl text-lg leading-relaxed mt-4 border-l-4 border-secondary pl-6">
            {verificationResultsData.header.description}
          </p>
        </header>

        {/* Verification Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">

          {/* Left Side: Detailed Verification Points */}
          <div className="lg:col-span-8 space-y-4">
            {verificationResultsData.points.map((point, index) => (
              <div key={point.id} className={`reveal point-${index} bg-surface-container-lowest p-8 rounded-sm shadow-sm border-l-8 border-primary group hover:bg-white hover:shadow-xl transition-all duration-500`}>
                <div className="flex justify-between items-center">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-[0.2em]">Metadata Point {point.id}</span>
                    <h3 className="text-2xl font-bold tracking-tight text-primary">{point.title}</h3>
                  </div>
                  <img src="/ccircle.png" alt="verified" className="animated-check inline-block" style={{ width: "32px", height: "32px", objectFit: "contain" }} />
                </div>
              </div>
            ))}
          </div>

          {/* Right Side: Logistics Data Sidebar */}
          <div className="lg:col-span-4 sticky top-32 space-y-8 animate-fade-up" style={{ animationDelay: '0.3s' }}>
            <div className="bg-primary p-8 text-on-primary rounded-sm shadow-xl relative overflow-hidden group">
              {/* Subtle pulsing gradient background */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary to-secondary/10 opacity-50"></div>

              <div className="relative z-10">
                <h4 className="text-[10px] font-bold tracking-[0.3em] uppercase mb-6 text-white/60">Final Hash Signature</h4>
                <div className="font-mono text-sm break-all opacity-90 leading-relaxed tracking-wider">
                  {verificationResultsData.sidebar.hash}
                </div>

                <div className="mt-8 pt-8 border-t border-white/10">
                  <div className="flex justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-white/50">Verified At</span>
                    <span className="text-xs font-bold">{verificationResultsData.sidebar.verifiedAt}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[10px] uppercase font-bold text-white/50">Nodes Checked</span>
                    <span className="text-xs font-bold text-secondary">{verificationResultsData.sidebar.nodesChecked}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="relative h-64 bg-primary rounded-sm overflow-hidden group border border-white/5 shadow-2xl">
              <img
                alt="Industrial Hub"
                className="w-full h-full object-cover grayscale brightness-50 contrast-125 transition-transform duration-700 group-hover:scale-110"
                src={verificationResultsData.sidebar.hubImage}
              />

              {/* Scanning Animation */}
              <div className="scanning-overlay absolute inset-0 bg-[linear-gradient(transparent_0%,rgba(227,30,36,0.1)_50%,transparent_100%)] h-[20%] w-full pointer-events-none animate-scan-line"></div>
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(0,0,0,0)_0%,rgba(0,0,0,0.6)_100%)]"></div>

              <div className="absolute bottom-4 left-4 right-4 flex flex-col gap-1 z-20">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_8px_#E31E24]"></div>
                  <p className="text-[9px] font-black uppercase tracking-[0.3em] text-white">Live Visual Confirmation</p>
                </div>
                <p className="text-xs font-bold text-white/80">Terminal Hub: Port Area 7G</p>
              </div>
            </div>

            <button className="btn-glow relative overflow-hidden shadow-[0_0_15px_rgba(227,30,36,0.2)] hover:shadow-[0_0_30px_rgba(227,30,36,0.5)] hover:bg-[#f12a31] transition-all w-full bg-secondary text-white py-5 font-black uppercase tracking-[0.2em] text-sm rounded-sm active:scale-[0.98]">
              Generate Final Certificate
            </button>
          </div>
        </div>
      </main>

      <footer className="relative z-10 w-full py-16 bg-white border-t border-outline-variant/10">
        <div className="max-w-7xl mx-auto px-8 flex flex-col md:flex-row justify-between items-center gap-10">
          <div className="text-xl font-black text-primary tracking-tighter uppercase flex items-center gap-2">
            <span className="w-6 h-6 bg-secondary flex items-center justify-center text-white text-xs">C</span>
            CLEAR PATH
          </div>
          <div className="flex flex-wrap justify-center gap-10">
            <a className="font-inter text-[10px] tracking-[0.2em] uppercase text-zinc-500 hover:text-secondary transition-colors font-bold" href="#sec">Security</a>
            <a className="font-inter text-[10px] tracking-[0.2em] uppercase text-zinc-500 hover:text-secondary transition-colors font-bold" href="#tos">Terms of Service</a>
            <a className="font-inter text-[10px] tracking-[0.2em] uppercase text-zinc-500 hover:text-secondary transition-colors font-bold" href="#api">API Documentation</a>
            <a className="font-inter text-[10px] tracking-[0.2em] uppercase text-zinc-500 hover:text-secondary transition-colors font-bold" href="#support">Support</a>
          </div>
          <div className="font-inter text-[10px] tracking-[0.2em] uppercase text-zinc-400 font-bold">
            © 2024 CLEAR PATH INDUSTRIAL. ALL RIGHTS RESERVED.
          </div>
        </div>
      </footer>
    </div>
  );
};
