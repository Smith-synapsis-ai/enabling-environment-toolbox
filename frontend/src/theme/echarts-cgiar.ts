import * as echarts from 'echarts';

export const CGIAR_COLORS = [
  '#1B3B2F', // dark green
  '#2D5A3D', // mid green
  '#4CAF50', // accent green
  '#1565C0', // blue
  '#42A5F5', // light blue
  '#E65100', // dark orange
  '#FF9800', // orange
  '#00695C', // dark teal
  '#26A69A', // teal
  '#7B1FA2', // dark purple
  '#AB47BC', // purple
  '#C62828', // red
];

const themeObj = {
  color: CGIAR_COLORS,
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  },
  title: {
    textStyle: {
      color: '#1B3B2F',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontWeight: 600,
      fontSize: 14,
    },
  },
  legend: {
    textStyle: {
      color: '#555',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontSize: 12,
    },
  },
  tooltip: {
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#e0e0e0',
    borderWidth: 1,
    textStyle: {
      color: '#333',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontSize: 12,
    },
    extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.1);',
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#ccc' } },
    axisTick: { lineStyle: { color: '#ccc' } },
    axisLabel: {
      color: '#666',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontSize: 11,
    },
    splitLine: { lineStyle: { color: '#f0f0f0' } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: '#ccc' } },
    axisTick: { lineStyle: { color: '#ccc' } },
    axisLabel: {
      color: '#666',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontSize: 11,
    },
    splitLine: { lineStyle: { color: '#f0f0f0' } },
  },
  line: {
    smooth: true,
    symbolSize: 4,
    lineStyle: { width: 2 },
  },
  bar: {
    barMaxWidth: 40,
    itemStyle: {
      borderRadius: [2, 2, 0, 0],
    },
  },
  pie: {
    itemStyle: {
      borderColor: '#fff',
      borderWidth: 2,
    },
  },
  gauge: {
    axisLine: {
      lineStyle: {
        color: [
          [0.6, '#E65100'],
          [0.8, '#FF9800'],
          [1, '#4CAF50'],
        ],
      },
    },
  },
};

echarts.registerTheme('cgiar', themeObj);
