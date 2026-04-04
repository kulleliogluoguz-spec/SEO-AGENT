/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    turbo: {
      resolveAlias: {
        // Turbopack (Next.js 14) fails to resolve react-dom/client via the
        // package.json exports map in its browser runtime. require.resolve()
        // gives Turbopack the absolute file path, bypassing exports-map lookup.
        'react-dom/client': require.resolve('react-dom/client'),
      },
    },
  },
}

module.exports = nextConfig
