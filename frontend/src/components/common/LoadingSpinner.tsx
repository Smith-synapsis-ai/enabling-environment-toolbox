import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  message?: string;
}

export default function LoadingSpinner({ size = 24, className = '', message }: LoadingSpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 ${className}`}>
      <Loader2 size={size} className="animate-spin text-cgiar-accent" />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  );
}
