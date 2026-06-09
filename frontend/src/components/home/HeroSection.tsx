import { useState } from 'react';
import { SendHorizonal } from 'lucide-react';
import BackgroundCarousel from './BackgroundCarousel';
import MetricsBar from './MetricsBar';

interface HeroSectionProps {
  onSendMessage: (message: string) => void;
}

export default function HeroSection({ onSendMessage }: HeroSectionProps) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <section className="relative min-h-screen flex flex-col">
      <BackgroundCarousel isBlurred={false} />

      {/* Gradient overlay: dark green top fading to a hint of purple at bottom */}
      <div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background: 'linear-gradient(180deg, rgba(3,53,41,0.15) 0%, rgba(3,53,41,0.05) 40%, rgba(121,4,180,0.08) 100%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 pt-16">
        {/* S4I emblem watermark behind title */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.04]">
          <img
            src="/branding/individual-block.svg"
            alt=""
            className="w-64 h-64"
            aria-hidden="true"
          />
        </div>

        {/* Title block */}
        <div className="text-center mb-10 relative">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold text-white tracking-tight mb-3"
              style={{ textShadow: '0 2px 20px rgba(0,0,0,0.3)' }}>
            Enabling Environment
          </h1>
          <p className="text-lg sm:text-xl text-white/80 font-light tracking-wide">
            The tools, the cases, the science
          </p>
        </div>

        {/* Chat input */}
        <form onSubmit={handleSubmit} className="w-full max-w-2xl px-4">
          <div className="relative group">
            <label htmlFor="hero-chat-input" className="sr-only">Describe your project or problem</label>
            <input
              id="hero-chat-input"
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Describe your project or problem. A few follow-up questions will help us find the most relevant tools and evidence."
              className="w-full px-6 py-4 pr-14 bg-white rounded-full text-gray-800 text-sm sm:text-base placeholder-gray-500 shadow-lg focus:outline-none focus:ring-2 focus:ring-s4i-purple/40 focus:shadow-xl focus:shadow-s4i-purple/10 transition-all"
            />
            <button
              type="submit"
              disabled={!inputValue.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center text-white transition-all disabled:bg-gray-300 hover:shadow-lg active:scale-95"
              style={{
                background: inputValue.trim()
                  ? 'linear-gradient(135deg, #2D5A3D, #7904B4)'
                  : undefined,
              }}
              aria-label="Send message"
            >
              <SendHorizonal size={18} aria-hidden="true" />
            </button>
          </div>
        </form>
      </div>

      {/* Metrics bar at bottom */}
      <div className="relative z-10">
        <MetricsBar />
      </div>
    </section>
  );
}
