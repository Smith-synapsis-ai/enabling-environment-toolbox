import { useState, useEffect } from 'react';

interface BackgroundCarouselProps {
  isBlurred?: boolean;
}

export default function BackgroundCarousel({ isBlurred = false }: BackgroundCarouselProps) {
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
    </>
  );
}
