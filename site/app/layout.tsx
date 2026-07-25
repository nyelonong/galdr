import type { Metadata } from "next";
import { headers } from "next/headers";
import "@fontsource-variable/newsreader/wght.css";
import "@fontsource/ibm-plex-mono/400.css";
import { siteUrlFromHeaders } from "./site-url";
import "./globals.css";

export const siteMetadata = {
  title: "galdr | Evidence-gated engineering for coding agents",
  description:
    "galdr routes each request, requires a failing test before production code, and records fresh evidence before work is called done.",
  icons: { icon: "/favicon.svg" },
} satisfies Metadata;

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const canonicalUrl = siteUrlFromHeaders(requestHeaders);
  const socialImageUrl = new URL("/og.png", canonicalUrl).toString();

  return {
    ...siteMetadata,
    metadataBase: canonicalUrl,
    alternates: { canonical: canonicalUrl.toString() },
    openGraph: { images: [socialImageUrl] },
    twitter: { card: "summary_large_image", images: [socialImageUrl] },
  };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
