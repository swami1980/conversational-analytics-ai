/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        amazon: {
          dark: '#131921',
          nav: '#232F3E',
          orange: '#FF9900',
          'orange-hover': '#E88B00',
          blue: '#146EB4',
          light: '#F3F3F3',
        },
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-dot': 'pulse 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
