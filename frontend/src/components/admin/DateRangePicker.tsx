interface DateRangePickerProps {
  days: number;
  onChange: (days: number) => void;
}

const PRESETS = [
  { label: '7d', value: 7 },
  { label: '30d', value: 30 },
  { label: '90d', value: 90 },
  { label: 'All', value: 365 },
] as const;

export default function DateRangePicker({ days, onChange }: DateRangePickerProps) {
  return (
    <div className="flex gap-1">
      {PRESETS.map(preset => (
        <button
          key={preset.value}
          onClick={() => onChange(preset.value)}
          className={`px-3 py-1 text-sm rounded-full font-medium transition-colors ${
            days === preset.value
              ? 'bg-cgiar-accent text-white shadow-sm'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
}
