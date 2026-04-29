import { Globe2, Shield, Target, Users, Zap } from "lucide-react";

const values = [
  {
    icon: Shield,
    title: "Trust & Safety",
    description:
      "We're committed to making online marketplaces safer by helping buyers make informed decisions.",
  },
  {
    icon: Zap,
    title: "Speed & Practicality",
    description:
      "Our checks are fast and transparent, using image forensics that can run locally on a simple backend.",
  },
  {
    icon: Target,
    title: "Transparency",
    description:
      "We explain what we find and why it matters. No black boxes, just clear signals.",
  },
  {
    icon: Users,
    title: "User-First Design",
    description:
      "Complex image analysis made simple for everyday marketplace decisions.",
  },
];

export default function About() {
  return (
    <div className="min-h-screen px-4 pb-12 pt-24">
      <div className="mx-auto max-w-4xl">
        <div className="mb-16 text-center">
          <h1 className="mb-4 text-3xl font-bold sm:text-4xl">
            About <span className="gradient-text">FraudLens</span>
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            Helping buyers make safer secondhand marketplace decisions with forensic image verification.
          </p>
        </div>

        <div className="glow-violet mb-12 rounded-2xl border border-border bg-card p-8">
          <h2 className="mb-4 text-2xl font-bold">Our Mission</h2>
          <p className="mb-4 text-muted-foreground leading-relaxed">
            Marketplace listings can use stolen images, edited photos, or generated product shots.
            FraudLens gives buyers a quick way to inspect an image before trusting a listing.
          </p>
          <p className="text-muted-foreground leading-relaxed">
            The current analyzer uses seven layers: EXIF metadata, ELA artifacts, noise
            patterns, edge consistency, screenshot-like structure, AI-like signal heuristics,
            and Reverse Image Search. It is an aid for decision-making, not proof of authenticity.
          </p>
        </div>

        <div className="mb-12">
          <h2 className="mb-8 text-center text-2xl font-bold">Our Values</h2>
          <div className="grid gap-6 sm:grid-cols-2">
            {values.map((value) => (
              <div
                key={value.title}
                className="rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/50"
              >
                <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20">
                  <value.icon className="size-6 text-primary" />
                </div>
                <h3 className="mb-2 text-lg font-semibold">{value.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {value.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-8">
          <h2 className="mb-6 text-2xl font-bold">How Our Analysis Works</h2>
          <div className="space-y-6">
            <div>
              <h3 className="mb-2 font-semibold text-primary">Metadata Extraction</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                We examine EXIF data for camera information, capture dates, and editing software.
                Missing or edited metadata can be a useful warning sign.
              </p>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-primary">Forensic Signal Checks</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                OpenCV checks look at recompression, JPEG block artifacts, edge consistency,
                noise irregularity, and sharpness. These signals can reveal edits or heavy processing.
              </p>
            </div>
            <div>
              <h3 className="mb-2 flex items-center gap-2 font-semibold text-primary">
                <Globe2 className="size-4" />
                Reverse Image Search
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                SerpAPI-powered reverse search checks whether a photo appears online already,
                including reused listings, stock-photo sites, and copied seller images.
              </p>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-primary">AI-Like Signal Estimate</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                The AI probability is a heuristic score based on forensic signals. It is not a
                trained classifier and should not be treated as a definitive AI detector.
              </p>
            </div>
            <div>
              <h3 className="mb-2 font-semibold text-primary">Trust Score Calculation</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                The signals are weighted into a 0-100 trust score with clear risk indicators
                for quick review.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-6">
          <h3 className="mb-2 font-semibold text-yellow-400">Important Disclaimer</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            FraudLens provides automated analysis to assist decision-making, but results are not
            100% accurate. Always combine the report with seller verification, video calls,
            secure payment methods, and common-sense checks.
          </p>
        </div>
      </div>
    </div>
  );
}
