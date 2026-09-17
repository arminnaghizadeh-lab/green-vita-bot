import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AnimatePresence,
  motion,
  useInView,
} from "framer-motion";
import { Menu, X, ArrowUpLeft } from "lucide-react";
import "./index.css";

const VIDEO =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260619_191346_9d19d66e-86a4-47f7-8dc6-712c1788c3b2.mp4";

function StaggeredFade({ text }: { text: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10%" });

  return (
    <span ref={ref} className="block">
      {text.split("").map((char, i) => (
        <motion.span
          key={`${text}-${i}`}
          initial={{ opacity: 0, y: 18 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.45, delay: i * 0.07, ease: "easeOut" }}
          className="inline-block"
        >
          {char === " " ? "\u00A0" : char}
        </motion.span>
      ))}
    </span>
  );
}

function App() {
  const [open, setOpen] = useState(false);

  const links = [
    ["خدمات", "#services"],
    ["تشخیص", "#diagnosis"],
    ["درباره ما", "/about/"],
    ["رزرو ویزیت", "/booking/"],
  ];

  return (
    <section className="relative min-h-screen overflow-hidden bg-[#010101]">
      <video
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 h-full w-full object-cover object-center"
      >
        <source src={VIDEO} type="video/mp4" />
      </video>

      <div className="absolute inset-0 bg-black/45" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/65 via-black/25 to-black/70" />

      <nav className="relative z-30 flex items-center justify-between px-5 py-5 sm:px-8 md:px-12 md:justify-center">
        <a
          href="/"
          className="text-sm font-light uppercase tracking-[.25em] text-white md:absolute md:right-12"
        >
          GREEN VITA
        </a>

        <div className="hidden items-center gap-10 md:flex">
          {links.map(([label, href]) => (
            <a
              key={label}
              href={href}
              className="text-xs font-light uppercase tracking-[.2em] text-white/80 transition duration-300 hover:text-white"
            >
              {label}
            </a>
          ))}
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          className="flex h-11 w-11 items-center justify-center text-white md:hidden"
          aria-label={open ? "بستن منو" : "باز کردن منو"}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="mobile-menu-glass fixed left-4 right-4 top-16 z-50 flex flex-col items-center gap-5 rounded-2xl py-8 md:hidden"
          >
            {links.map(([label, href], i) => (
              <motion.a
                key={label}
                href={href}
                onClick={() => setOpen(false)}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 + i * 0.06 }}
                className="text-sm font-light uppercase tracking-[.25em] text-white/90"
              >
                {label}
              </motion.a>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-10 flex min-h-[calc(100vh-80px)] flex-col items-center justify-center px-5 pb-16 pt-12 text-center sm:px-8 sm:pt-16 md:pt-24">
        <h1 className="font-garamond mb-6 text-5xl font-normal leading-[1.08] tracking-tight text-white sm:mb-8 sm:text-6xl md:text-8xl lg:text-9xl">
          <StaggeredFade text="GREEN VITA" />
          <StaggeredFade text="زبان گیاهت را بفهم" />
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.6 }}
          className="mb-8 max-w-xs text-sm font-light leading-relaxed text-white/70 sm:mb-10 sm:max-w-md sm:text-base md:text-lg"
        >
          تشخیص تخصصی، ویزیت و مراقبت علمی برای گیاهانی که دوستشان داری.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 2 }}
          className="flex flex-col items-center gap-3 sm:flex-row"
        >
          <a
            href="/booking/"
            className="inline-flex min-h-12 items-center justify-center gap-3 rounded-full bg-[#8BC53D] px-8 py-3.5 text-sm font-medium text-[#022F12] shadow-[0_12px_35px_rgba(139,197,61,.28)] transition duration-300 hover:scale-[1.02] hover:bg-[#9ED84A] sm:px-10"
          >
            رزرو ویزیت
            <ArrowUpLeft size={18} />
          </a>

          <a
            href="/booking/track/"
            className="liquid-glass inline-flex min-h-12 items-center justify-center rounded-full px-8 py-3.5 text-sm font-light tracking-[.04em] text-white sm:px-10"
          >
            پیگیری رزرو
          </a>
        </motion.div>
      </div>
    </section>
  );
}

const root = document.getElementById("root");

if (root) {
  createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
