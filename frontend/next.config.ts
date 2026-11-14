import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    return [{ source: '/api/v1/:path*', destination: `${process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'}/api/v1/:path*` }];
  },
  poweredByHeader: false,
  async headers() {
    return [{ source: '/:path*', headers: [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'Content-Security-Policy', value: "base-uri 'self'; form-action 'self'; object-src 'none'; frame-ancestors 'none'" },
    ] }];
  },
};

export default nextConfig;
