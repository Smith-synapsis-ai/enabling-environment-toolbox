import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SendHorizonal, LayoutGrid } from 'lucide-react';
import BackgroundCarousel from './BackgroundCarousel';
import MetricsBar from './MetricsBar';

interface HeroSectionProps {
  /** Called with the challenge text when the user submits (e.g. analytics). */
  onSubmitChallenge?: (message: string) => void;
}

export default function HeroSection({ onSubmitChallenge }: HeroSectionProps) {
  const [inputValue, setInputValue] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = inputValue.trim();
    if (text) {
      onSubmitChallenge?.(text);
      // Launch the full Assistant experience with the challenge pre-filled and
      // auto-sent once its WebSocket opens (AssistantPage reads location.state).
      navigate('/assistant', { state: { initialChallenge: text } });
      setInputValue('');
    }
  };

  return (
    <section className="relative min-h-screen flex flex-col">
      <BackgroundCarousel isBlurred={false} />

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 pt-16">
        {/* Title block */}
        <div className="text-center mb-10">
          <div className="flex items-center justify-center gap-3 mb-3">
            <LayoutGrid size={28} className="text-white/80" />
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight">
              Enabling Environment
            </h1>
          </div>
          <p className="text-lg sm:text-xl text-white/80 font-light">
            The tools, the cases, the science
          </p>
        </div>

        {/* Chat input */}
        <form onSubmit={handleSubmit} className="w-full max-w-2xl px-4">
          <div className="relative">
            <label htmlFor="hero-chat-input" className="sr-only">Describe your project or problem</label>
            <input
              id="hero-chat-input"
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Describe your project or problem. A few follow-up questions will help us find the most relevant tools and evidence."
              className="w-full px-6 py-4 pr-14 bg-white rounded-full text-gray-800 text-sm sm:text-base placeholder-gray-500 shadow-lg focus:outline-none focus:ring-2 focus:ring-cgiar-accent/50 transition-shadow"
            />
            <button
              type="submit"
              disabled={!inputValue.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-cgiar-accent hover:bg-cgiar-green disabled:bg-gray-300 rounded-full flex items-center justify-center text-white transition-colors"
              aria-label="Send message"
            >
              <SendHorizonal size={18} />
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
