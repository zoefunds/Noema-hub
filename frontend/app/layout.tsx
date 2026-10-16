import type { Metadata } from "next";
import { Chrome } from "@/components/Chrome";
import "./globals.css";

export const metadata: Metadata = {
  title: "Noema — Public research, settled by evidence",
  description: "A GenLayer protocol for funding decisive public-source research.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-scroll-behavior="smooth"><body><Chrome>{children}</Chrome></body></html>;
}
