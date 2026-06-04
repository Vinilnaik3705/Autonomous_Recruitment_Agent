import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import Providers from "./providers";
import ThemeInit from "@/components/ThemeInit";
import "../index.css"; // Reuse existing css or make it globals.css

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

export const metadata: Metadata = {
  title: "Antigravity Recruitment | Enterprise AI Hiring Platform",
  description: "Accelerate your talent acquisition with advanced AI resume analysis, automated scheduling, and end-to-end recruitment pipelines.",
  keywords: ["recruitment", "AI resume screening", "hiring automation", "online assessment", "interview scheduling"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="light" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{document.documentElement.classList.remove("light","dark");document.documentElement.classList.add("light");document.documentElement.style.colorScheme="light";}catch(e){}})();`,
          }}
        />
      </head>
      <body className={`${outfit.variable} font-sans bg-[#f5f7fb] text-gray-900 antialiased min-h-screen theme-body`}>
        <ThemeInit />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
