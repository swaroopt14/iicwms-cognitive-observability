/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Dark theme palette (Datadog-inspired)
        'surface': {
          'primary': '#1a1a2e',
          'secondary': '#16213e',
          'tertiary': '#0f0f1a',
          'elevated': '#252542',
        },
        'accent': {
          'purple': '#7c3aed',
          'blue': '#3b82f6',
          'cyan': '#06b6d4',
        },
        'severity': {
          'critical': '#ef4444',
          'high': '#f97316',
          'medium': '#eab308',
          'low': '#3b82f6',
          'info': '#6b7280',
        },
        'status': {
          'healthy': '#10b981',
          'degraded': '#f59e0b',
          'critical': '#ef4444',
        }
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
