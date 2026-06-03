/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f5f7ff',
          100: '#ebf0ff',
          200: '#d6e0ff',
          300: '#b3c7ff',
          400: '#85a2ff',
          500: '#5272ff', // Main Brand Accent
          600: '#3d52e6',
          700: '#2f3cb3',
          800: '#262f8c',
          900: '#212870',
        },
      },
    },
  },
  plugins: [],
}
