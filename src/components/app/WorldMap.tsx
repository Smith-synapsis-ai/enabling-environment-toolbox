interface WorldMapProps {
  selectedRegion?: string
  onRegionClick?: (region: string) => void
}

// Simplified SVG world map with key regions as clickable paths
export function WorldMap({ selectedRegion, onRegionClick }: WorldMapProps) {
  const regions = [
    {
      id: 'East Africa',
      label: 'East Africa',
      count: 8,
      // Simplified path for East Africa region
      cx: 310, cy: 195, rx: 28, ry: 22,
    },
    {
      id: 'West Africa',
      label: 'West Africa',
      count: 6,
      cx: 255, cy: 188, rx: 25, ry: 20,
    },
    {
      id: 'Sub-Saharan Africa',
      label: 'Sub-Saharan Africa',
      count: 12,
      cx: 285, cy: 220, rx: 35, ry: 28,
    },
    {
      id: 'South Asia',
      label: 'South Asia',
      count: 9,
      cx: 390, cy: 165, rx: 30, ry: 22,
    },
    {
      id: 'Southeast Asia',
      label: 'SE Asia',
      count: 7,
      cx: 440, cy: 178, rx: 28, ry: 20,
    },
    {
      id: 'Latin America',
      label: 'Latin America',
      count: 5,
      cx: 165, cy: 220, rx: 30, ry: 35,
    },
  ]

  function getIntensityColor(count: number): string {
    if (count >= 13) return '#00524D'
    if (count >= 7) return '#007A72'
    if (count >= 4) return '#4CAF8A'
    return '#B2DDD4'
  }

  return (
    <div className="w-full">
      <svg
        viewBox="0 0 580 300"
        className="w-full h-auto"
        style={{ maxHeight: 260 }}
      >
        {/* Ocean background */}
        <rect width="580" height="300" fill="#EBF8FF" rx="8" />

        {/* Simplified continent shapes */}
        {/* North America */}
        <path
          d="M 60 60 L 140 50 L 160 90 L 170 130 L 150 160 L 130 170 L 110 165 L 90 150 L 70 130 L 55 100 Z"
          fill="#D1FAE5"
          stroke="#A7F3D0"
          strokeWidth="1"
        />
        {/* Latin America */}
        <path
          d="M 120 175 L 155 170 L 175 185 L 185 215 L 185 250 L 170 265 L 150 260 L 135 240 L 120 215 L 110 195 Z"
          fill={selectedRegion === 'Latin America' ? '#007A72' : getIntensityColor(5)}
          stroke="#fff"
          strokeWidth="1"
          className="cursor-pointer transition-colors duration-200 hover:opacity-80"
          onClick={() => onRegionClick?.('Latin America')}
          style={{ opacity: selectedRegion && selectedRegion !== 'Latin America' ? 0.5 : 1 }}
        />
        {/* Europe */}
        <path
          d="M 230 50 L 280 45 L 295 65 L 280 85 L 255 90 L 235 80 L 225 65 Z"
          fill="#D1FAE5"
          stroke="#A7F3D0"
          strokeWidth="1"
        />
        {/* Middle East */}
        <path
          d="M 290 95 L 340 90 L 355 110 L 345 130 L 310 135 L 290 120 Z"
          fill="#E9F7EF"
          stroke="#C6ECD8"
          strokeWidth="1"
        />
        {/* Africa */}
        <path
          d="M 240 110 L 285 105 L 320 110 L 340 130 L 345 165 L 335 205 L 315 230 L 290 240 L 265 235 L 245 210 L 230 175 L 225 145 L 230 120 Z"
          fill="#E9F7EF"
          stroke="#A7F3D0"
          strokeWidth="1"
        />
        {/* West Africa highlight */}
        <ellipse
          cx={255} cy={170}
          rx={28} ry={22}
          fill={selectedRegion === 'West Africa' ? '#007A72' : getIntensityColor(6)}
          stroke="#fff"
          strokeWidth="1.5"
          className="cursor-pointer transition-colors duration-200 hover:opacity-80"
          onClick={() => onRegionClick?.('West Africa')}
          style={{ opacity: selectedRegion && selectedRegion !== 'West Africa' ? 0.5 : 1 }}
        />
        {/* East Africa highlight */}
        <ellipse
          cx={310} cy={178}
          rx={26} ry={20}
          fill={selectedRegion === 'East Africa' ? '#007A72' : getIntensityColor(8)}
          stroke="#fff"
          strokeWidth="1.5"
          className="cursor-pointer transition-colors duration-200 hover:opacity-80"
          onClick={() => onRegionClick?.('East Africa')}
          style={{ opacity: selectedRegion && selectedRegion !== 'East Africa' ? 0.5 : 1 }}
        />
        {/* Sub-Saharan Africa highlight */}
        <ellipse
          cx={285} cy={208}
          rx={32} ry={24}
          fill={selectedRegion === 'Sub-Saharan Africa' ? '#007A72' : getIntensityColor(12)}
          stroke="#fff"
          strokeWidth="1.5"
          className="cursor-pointer transition-colors duration-200 hover:opacity-80"
          onClick={() => onRegionClick?.('Sub-Saharan Africa')}
          style={{ opacity: selectedRegion && selectedRegion !== 'Sub-Saharan Africa' ? 0.5 : 1 }}
        />
        {/* Russia / Central Asia */}
        <path
          d="M 295 40 L 500 35 L 510 70 L 450 80 L 380 75 L 295 70 Z"
          fill="#D1FAE5"
          stroke="#A7F3D0"
          strokeWidth="1"
        />
        {/* South/Southeast Asia */}
        <path
          d="M 360 90 L 475 85 L 490 120 L 480 155 L 455 170 L 420 175 L 380 165 L 355 140 L 350 110 Z"
          fill="#E9F7EF"
          stroke="#A7F3D0"
          strokeWidth="1"
        />
        {/* South Asia highlight */}
        <ellipse
          cx={395} cy={148}
          rx={32} ry={25}
          fill={selectedRegion === 'South Asia' ? '#007A72' : getIntensityColor(9)}
          stroke="#fff"
          strokeWidth="1.5"
          className="cursor-pointer transition-colors duration-200 hover:opacity-80"
          onClick={() => onRegionClick?.('South Asia')}
          style={{ opacity: selectedRegion && selectedRegion !== 'South Asia' ? 0.5 : 1 }}
        />
        {/* Southeast Asia highlight */}
        <ellipse
          cx={452} cy={160}
          rx={28} ry={20}
          fill={selectedRegion === 'Southeast Asia' ? '#007A72' : getIntensityColor(7)}
          stroke="#fff"
          strokeWidth="1.5"
          className="cursor-pointer transition-colors duration-200 hover:opacity-80"
          onClick={() => onRegionClick?.('Southeast Asia')}
          style={{ opacity: selectedRegion && selectedRegion !== 'Southeast Asia' ? 0.5 : 1 }}
        />
        {/* Australia */}
        <path
          d="M 450 200 L 510 195 L 530 225 L 520 255 L 490 265 L 455 255 L 440 230 L 445 210 Z"
          fill="#D1FAE5"
          stroke="#A7F3D0"
          strokeWidth="1"
        />

        {/* Region labels */}
        {regions.map(r => (
          <text
            key={r.id}
            x={r.cx}
            y={r.cy + 3}
            textAnchor="middle"
            fontSize="8"
            fill="white"
            fontWeight="600"
            className="pointer-events-none select-none"
          >
            {r.label}
          </text>
        ))}

        {/* Legend */}
        <g transform="translate(18, 240)">
          <text x="0" y="0" fontSize="7" fill="#4A5568" fontWeight="600">Activity density:</text>
          {[
            { color: '#B2DDD4', label: '1-6' },
            { color: '#4CAF8A', label: '7-12' },
            { color: '#007A72', label: '13-20' },
            { color: '#00524D', label: '20+' },
          ].map((item, i) => (
            <g key={item.label} transform={`translate(${i * 50}, 10)`}>
              <rect width="16" height="8" rx="2" fill={item.color} />
              <text x="20" y="8" fontSize="7" fill="#4A5568">{item.label}</text>
            </g>
          ))}
        </g>
      </svg>
      <p className="text-[10px] text-gray-400 mt-2 italic leading-relaxed">
        Data based on curated CGIAR tools and documented reform experiences across countries. Click a region to filter results.
      </p>
    </div>
  )
}
