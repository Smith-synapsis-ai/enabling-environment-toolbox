import { useCallback } from 'react';
import HeroSection from '../components/home/HeroSection';

interface HomePageProps {
  onToolViewed?: () => void;
  onSearchPerformed?: () => void;
}

export default function HomePage({ onSearchPerformed }: HomePageProps) {
  // The hero challenge box now launches the real Assistant (/assistant) with
  // the typed challenge pre-filled and auto-sent. The legacy static-stub
  // useChat hook / ChatInterface path has been removed.
  const handleSubmitChallenge = useCallback((_msg: string) => {
    onSearchPerformed?.();
  }, [onSearchPerformed]);

  return (
    <div className="relative">
      <HeroSection onSubmitChallenge={handleSubmitChallenge} />
    </div>
  );
}
