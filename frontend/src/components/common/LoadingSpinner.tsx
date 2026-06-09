import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  message?: string;
}

export default function LoadingSpinner({ size = 24, className = '', message }: LoadingSpinnerProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 ${className}`}
      role="status"
      aria-label={message || 'Loading'}
    >
      <Loader2 size={size} className="animate-spin text-cgiar-accent" aria-hidden="true" />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  );
}
