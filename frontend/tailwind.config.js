/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cgiar': {
          'dark': '#033529',
          'green': '#2D5A3D',
          'accent': '#4CAF50',
          'light': '#F5F5F5',
        },
        's4i': {
          'purple': '#D685FF',
          'purple-deep': '#7904B4',
          'purple-light': '#DD9AFF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
