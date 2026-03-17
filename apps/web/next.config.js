/** @type {import('next').NextConfig} */
const nextConfig = {
  // 'standalone' output requires .next/standalone to be available — only for production builds
  // Remove for dev to keep things simple; re-enable when production Dockerfile is set up
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000', '0.0.0.0:3000'],
    },
  },
}

module.exports = nextConfig
