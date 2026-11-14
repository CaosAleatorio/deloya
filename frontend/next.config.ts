import type { NextConfig } from "next";

const allowedDevOrigins = [...new Set(['127.0.0.1', ...(process.env.DEV_ALLOWED_HOSTS ?? '').split(',').map((host) => host.trim().toLowerCase()).filter(Boolean)])];
for (const hostname of allowedDevOrigins) {
  let valid = false;
  try {
    const origin = new URL(`http://${hostname}`);
    valid = !/[\s/*?#@]/.test(hostname) && origin.hostname === hostname && origin.host === hostname;
  } catch { /* Invalid development hosts must fail closed. */ }
  if (!valid) throw new Error('DEV_ALLOWED_HOSTS must contain explicit hostnames separated by commas, without a scheme, port, path or wildcard.');
}

const nextConfig: NextConfig = {
  allowedDevOrigins,
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
