import forms from '@tailwindcss/forms';
import typography from '@tailwindcss/typography';

/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./src/**/*.{js,jsx,ts,tsx}",
      "./public/index.html",
      "./index.html"
    ],
    theme: {
      extend: {
        colors: {
          draft: {
            primary: '#3B82F6',
            secondary: '#64748B',
            success: '#10B981',
            warning: '#F59E0B',
            danger: '#EF4444',
          },
          position: {
            "1B": '#8B5CF6',
            OF: '#10B981',
            P: '#3B82F6',
            C: '#F97316',

          }
        },
        fontFamily: {
          sans: ['Inter', 'system-ui', 'sans-serif'],
          mono: ['JetBrains Mono', 'Monaco', 'monospace'],
        },
        animation: {
          'bounce-slow': 'bounce 2s infinite',
          'pulse-slow': 'pulse 3s infinite',
          'fadeIn': 'fadeIn 0.3s ease-in-out',
          'slideIn': 'slideIn 0.3s ease-out',
        },
        spacing: {
          '18': '4.5rem',
          '88': '22rem',
          '128': '32rem',
        },
        minHeight: {
          '12': '3rem',
          '16': '4rem',
          '20': '5rem',
        }
      },
    },

        plugins: [
          forms,
          typography,
        ],
  }