import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repo lives in an iCloud-synced folder; iCloud skips names ending in
  // .nosync, so it can't leave conflict copies ("routes.d 2.ts") in the build.
  distDir: ".next.nosync",
  /* config options here */
  cacheComponents: true,
  // Dev-only badge; bottom-left would cover the sidebar's charity name.
  devIndicators: { position: "bottom-right" },
  // Lets a phone on the same Wi-Fi use the dev server (http://<mac-ip>:3000);
  // dev-only, has no effect in a production build.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "*.local"],
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
