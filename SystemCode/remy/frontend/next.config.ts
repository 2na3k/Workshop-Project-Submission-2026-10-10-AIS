import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root: a stray package-lock.json in the home directory
  // sits above this project and would otherwise be inferred as the root.
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
