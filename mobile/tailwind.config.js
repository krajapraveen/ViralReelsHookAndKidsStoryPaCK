/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        void: '#070711',
        midnight: '#10101f',
        nebula: '#7c3aed',
        aurora: '#22d3ee',
        ember: '#fb7185',
        gold: '#facc15',
      },
      fontFamily: {
        sans: ['System'],
      },
    },
  },
  plugins: [],
};
