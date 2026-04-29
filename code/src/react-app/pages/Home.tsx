import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  Camera,
  CheckCircle2,
  FileCheck,
  Fingerprint,
  Globe2,
  Layers3,
  MessageSquareText,
  Radar,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Upload,
  Zap,
} from "lucide-react";
import { Button } from "@/react-app/components/ui/button";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

const features = [
  {
    icon: Camera,
    title: "EXIF Metadata",
    description: "Reads camera data, capture details, timestamps, and editing software indicators.",
  },
  {
    icon: Layers3,
    title: "ELA",
    description: "Measures compression artifacts that can appear after edits, resaves, or manipulation.",
  },
  {
    icon: Fingerprint,
    title: "Noise Analysis",
    description: "Checks whether image noise behaves consistently across different visual regions.",
  },
  {
    icon: Radar,
    title: "Edge Analysis",
    description: "Reviews edge density and sharpness signals for blur, screenshots, or overprocessing.",
  },
  {
    icon: ScanSearch,
    title: "Screenshot Detection",
    description: "Flags screenshot-like structure using metadata, aspect, edge, and visual layout signals.",
  },
  {
    icon: Bot,
    title: "AI-like Heuristic",
    description: "Combines visual signals into a deterministic synthetic-looking image heuristic.",
  },
  {
    icon: Globe2,
    title: "Reverse Image Search",
    description: "Checks whether a seller image appears elsewhere online through SerpAPI.",
  },
  {
    icon: MessageSquareText,
    title: "Google Vision OCR",
    description: "Detects listing text, phone numbers, invoice-like text, UI words, and watermarks.",
  },
  {
    icon: BadgeCheck,
    title: "Logo Detection",
    description: "Identifies brand logos such as Apple, Dell, Nike, Samsung, HP, and Lenovo.",
  },
];

const steps = [
  {
    icon: Upload,
    title: "Upload Image",
    description: "Add a marketplace photo from a listing, chat, screenshot, or seller message.",
  },
  {
    icon: Zap,
    title: "Analyze Signals",
    description: "FraudLens runs metadata, ELA, noise, edge, OCR, logo, web, and Vision checks.",
  },
  {
    icon: FileCheck,
    title: "Get Trust Report",
    description: "Review the score, findings, recommendations, and explainable score breakdown.",
  },
];

function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.45 }}
      className="mx-auto max-w-3xl text-center"
    >
      <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-300">
        <Sparkles className="size-4" />
        {eyebrow}
      </div>
      <h2 className="text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl lg:text-5xl">
        {title}
      </h2>
      <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-gray-300 sm:text-lg">
        {description}
      </p>
    </motion.div>
  );
}

export default function Home() {
  return (
    <div className="bg-[#0a0e1a] text-white">
      <section className="relative flex min-h-[90vh] items-center justify-center overflow-hidden px-4 py-20 sm:px-6 lg:px-8">
        <div className="pointer-events-none absolute inset-0 opacity-[0.06] [background-image:linear-gradient(rgba(0,212,255,0.7)_1px,transparent_1px),linear-gradient(90deg,rgba(124,58,237,0.65)_1px,transparent_1px)] [background-size:56px_56px]" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[42rem] w-[42rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="pointer-events-none absolute left-1/2 top-[54%] h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-violet-600/15 blur-3xl" />

        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          transition={{ duration: 0.55 }}
          className="relative mx-auto max-w-6xl text-center"
        >
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-300">
            <ShieldCheck className="size-4" />
            Marketplace Image Trust Checker
          </div>

          <h1 className="mx-auto mb-6 max-w-5xl text-center text-5xl font-extrabold leading-tight text-white sm:text-6xl lg:text-7xl">
            Verify seller images before you{" "}
            <span className="bg-gradient-to-r from-cyan-300 to-violet-400 bg-clip-text text-transparent">
              trust
            </span>{" "}
            the listing.
          </h1>

          <p className="mx-auto max-w-3xl text-lg leading-relaxed text-gray-300 sm:text-xl">
            FraudLens analyzes EXIF metadata, ELA artifacts, OCR text, logos,
            screenshots, reverse image search, and Google Vision signals to help
            you make safer secondhand marketplace decisions.
          </p>

          <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="h-14 rounded-xl bg-gradient-to-r from-cyan-400 to-violet-500 px-8 py-6 text-base font-semibold text-[#0a0e1a] shadow-lg shadow-cyan-500/25 transition-all hover:scale-[1.02] hover:shadow-[0_0_34px_rgba(0,212,255,0.28)]"
            >
              <Link to="/checker">
                Upload Photo
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </motion.div>
      </section>

      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <SectionHeader
            eyebrow="Trust Features"
            title="Every report is built from real image signals."
            description="Each feature contributes to an explainable trust score."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.4, delay: index * 0.03 }}
                className="flex min-h-[160px] flex-col gap-3 rounded-2xl border border-cyan-500/10 bg-[#111827]/80 p-6 transition-all hover:border-cyan-400/40 hover:shadow-[0_0_30px_rgba(0,212,255,0.12)]"
              >
                <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/15 to-violet-500/15">
                  <feature.icon className="size-5 text-cyan-300" />
                </div>
                <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                <p className="text-sm leading-6 text-gray-300">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <SectionHeader
            eyebrow="How It Works"
            title="A clean path from image to decision."
            description="Upload once, let FraudLens inspect the image, then review a clear marketplace trust report."
          />

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                variants={fadeUp}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.4, delay: index * 0.08 }}
                className="rounded-2xl border border-cyan-500/10 bg-[#111827]/80 p-6 text-center transition-all hover:border-cyan-400/40 hover:shadow-[0_0_30px_rgba(0,212,255,0.12)]"
              >
                <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 text-[#0a0e1a]">
                  <step.icon className="size-8" />
                </div>
                <div className="mx-auto mt-6 flex size-10 items-center justify-center rounded-full border border-cyan-500/20 bg-cyan-500/10 text-sm font-bold text-cyan-300">
                  {index + 1}
                </div>
                <h3 className="mt-5 text-xl font-semibold text-white">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-gray-300">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-24 sm:px-6 lg:px-8">
        <motion.div
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.45 }}
          className="mx-auto max-w-4xl rounded-2xl border border-cyan-500/10 bg-[#111827]/90 p-8 text-center shadow-2xl shadow-cyan-950/20 sm:p-10"
        >
          <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 text-[#0a0e1a]">
            <CheckCircle2 className="size-7" />
          </div>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-white sm:text-5xl">
            Ready to check a seller photo?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-gray-300 sm:text-lg">
            Run a marketplace image scan and get an explainable trust report in seconds.
          </p>
          <div className="mt-8">
            <Button
              asChild
              size="lg"
              className="h-14 rounded-xl bg-gradient-to-r from-cyan-400 to-violet-500 px-8 py-6 text-base font-semibold text-[#0a0e1a] shadow-lg shadow-cyan-500/25 transition-all hover:scale-[1.02] hover:shadow-[0_0_34px_rgba(0,212,255,0.28)]"
            >
              <Link to="/checker">
                Start Photo Check
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
