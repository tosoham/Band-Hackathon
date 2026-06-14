import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BandGate",
  description: "Cybersecurity RFP promise gate for Band of Agents Hackathon",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
