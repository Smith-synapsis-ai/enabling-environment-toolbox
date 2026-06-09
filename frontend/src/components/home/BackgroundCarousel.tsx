import { useState, useEffect } from 'react';

interface BackgroundCarouselProps {
  isBlurred?: boolean;
}

export default function BackgroundCarousel({ isBlurred = false }: BackgroundCarouselProps) {
  const [activeSlide] = useState(0);
  const totalSlides = 3;

  const [bgEnabled, setBgEnabled] = useState(() => {
    return localStorage.getItem('ee-bg-enabled') !== 'false'; // default true
  });

  // Listen for storage changes (cross-tab) and custom event (same-tab)
  useEffect(() => {
    const handleUpdate = () => {
      setBgEnabled(localStorage.getItem('ee-bg-enabled') !== 'false');
    };
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('ee-bg-toggle', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('ee-bg-toggle', handleUpdate);
    };
  }, []);

  return (
    <>
      {/* Background image / solid color with optional blur */}
      <div
        className="absolute inset-0 transition-all duration-500"
        style={{
          filter: isBlurred ? 'blur(4px) brightness(0.7)' : 'none',
        }}
      >
        {bgEnabled ? (
          <>
            <img
              src="/hero-bg.png"
              alt="Agricultural landscape"
              className="w-full h-full object-cover"
            />
            <div
              className="absolute inset-0"
              style={{ backgroundColor: 'rgba(20, 50, 35, 0.75)' }}
            />
          </>
        ) : (
          <div className="absolute inset-0" style={{ backgroundColor: '#1B3B2F' }} />
        )}
      </div>

      {/* Dot navigation — stays outside blur wrapper */}
      <div className="absolute bottom-28 right-8 flex flex-col gap-2 z-10">
        {Array.from({ length: totalSlides }).map((_, i) => (
          <button
            key={i}
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              i === activeSlide
                ? 'bg-white scale-110'
                : 'bg-white/40 hover:bg-white/60'
            }`}
            aria-label={`Slide ${i + 1}`}
          />
        ))}
      </div>
    </>
  );
}
