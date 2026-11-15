import type { NextConfig } from "next";

const cloudDeployment = ['production', 'preview'].includes(process.env.VERCEL_ENV ?? '') || process.env.VERCEL === '1' && process.env.VERCEL_ENV !== 'development';
const configuredBackend = process.env.BACKEND_URL;
if (cloudDeployment && !configuredBackend) throw new Error('BACKEND_URL must be configured before deploying to Vercel.');
const backendUrl = configuredBackend ?? 'http://127.0.0.1:8000';
let backendOrigin = '';
try {
  const parsed = new URL(backendUrl);
  const localHost = ['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname);
  if (!['http:', 'https:'].includes(parsed.protocol) || /[\s\\?#]/.test(backendUrl) || parsed.username || parsed.password || parsed.pathname !== '/' || cloudDeployment && (parsed.protocol !== 'https:' || localHost)) throw new Error();
  backendOrigin = parsed.origin;
} catch { throw new Error('BACKEND_URL must be an HTTP(S) origin without credentials, a path or query; Vercel deployments require a public HTTPS origin.'); }

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
    return [{ source: '/api/v1/:path*', destination: `${backendOrigin}/api/v1/:path*` }];
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
