import { Shield } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border bg-card/50 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          <div className="flex flex-col items-center gap-3 md:items-start">
            <div className="flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-violet-500">
                <Shield className="size-4 text-background" />
              </div>
              <span className="gradient-text text-lg font-bold">FraudLens</span>
            </div>
            <p className="max-w-md text-center text-sm text-muted-foreground md:text-left">
              Forensic image verification for safer buying decisions on secondhand marketplaces.
            </p>
          </div>

          <div className="text-center md:text-right">
            <p className="max-w-sm text-xs text-muted-foreground">
              <span className="font-medium text-foreground/70">Disclaimer:</span>{" "}
              Results are automated estimates and are not proof of authenticity.
            </p>
          </div>
        </div>

        <div className="mt-8 border-t border-border pt-6 text-center">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} FraudLens. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
