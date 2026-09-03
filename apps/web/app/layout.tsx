import type { Metadata } from "next";
import { I18nProvider } from "../lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "OCRWorkbench",
  description: "Self-hosted general and professional OCR workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body><I18nProvider>{children}</I18nProvider></body>
    </html>
  );
}
