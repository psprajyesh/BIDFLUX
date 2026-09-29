import type { NextConfig } from "next";

/**
 * The browser talks to FastAPI directly using NEXT_PUBLIC_API_URL.
 *
 * There is deliberately no dev proxy here: a single, explicit API base URL keeps the
 * local and deployed behaviour identical, and CORS on the backend is configured with an
 * exact-origin allow-list.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
};

export default nextConfig;
