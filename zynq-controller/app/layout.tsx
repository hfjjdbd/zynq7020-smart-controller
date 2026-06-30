import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ZYNQ7020 Smart Controller",
  description: "Web-based control for ZYNQ7020 development board",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
