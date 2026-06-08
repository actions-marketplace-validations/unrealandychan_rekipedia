/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  // Ensure that links do not have trailing slashes
  trailingSlash: false,
};

export default nextConfig;
