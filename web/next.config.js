/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Disable webpack optimization for env vars
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Force runtime env var reading
      config.externals = config.externals || []
    }
    return config
  },
}

module.exports = nextConfig

