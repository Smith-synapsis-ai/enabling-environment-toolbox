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
          // Darker accent for green TEXT/LINKS (and small solid buttons) on light
          // backgrounds. #4CAF50 only reaches ~2.5:1 on #F5F5F5. #15692F clears
          // WCAG AA 4.5:1 even on the lightest tinted pill bg (bg-cgiar-accent/10
          // ≈ #E4EEE5 → 5.7:1) and gives 6.8:1 for white text on a solid fill,
          // while staying visually "CGIAR green".
          'accent-dark': '#15692F',
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
