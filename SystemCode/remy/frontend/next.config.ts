import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root: a stray package-lock.json in the home directory
  // sits above this project and would otherwise be inferred as the root.
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    const calculatorUrl = "http://localhost:8081";
    return [{
      source: "/api/v1/calculate/cost-and-nutrition",
      destination: `${calculatorUrl}/api/v1/calculate/cost-and-nutrition`,    }];
  },
};

export default nextConfig;
