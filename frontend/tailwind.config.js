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
          // Darker accent for green TEXT/LINKS on light backgrounds — #4CAF50
          // only reaches ~2.5:1 on #F5F5F5, below WCAG AA's 4.5:1 for text.
          // #1B7E3C is ~5.3:1 on light while staying visually "CGIAR green".
          'accent-dark': '#1B7E3C',
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
