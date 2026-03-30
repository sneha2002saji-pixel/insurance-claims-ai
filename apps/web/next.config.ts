import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    turbopack: {
      root: path.resolve(__dirname, "../../"),
    },
  },
};

export default nextConfig;
