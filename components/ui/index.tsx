"use client";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import * as React from "react";
import { cn } from "@/lib/utils";

// shadcn/ui-style primitives (cva + Radix Slot + cn). Written by hand because the shadcn registry was unreachable at build time.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition disabled:pointer-events-none disabled:opacity-50 active:scale-[.98]",
  {
    variants: {
      variant: {
        default: "gradient-brand text-white shadow-md shadow-brand/25 hover:brightness-110",
        outline: "border border-border bg-card text-foreground hover:bg-soft",
        ghost: "text-foreground hover:bg-soft",
        danger: "bg-danger text-white hover:brightness-110",
      },
      size: { default: "h-11 px-5", sm: "h-9 px-3", icon: "h-10 w-10" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({ className, variant, size, asChild, ...props }: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export function Card({ className, ...p }: React.ComponentProps<"div">) {
  return <div className={cn("rounded-card border border-border bg-card p-5 shadow-sm shadow-brand/5", className)} {...p} />;
}

export const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(function Input({ className, ...p }, ref) {
  return <input ref={ref} className={cn("h-11 w-full rounded-xl border border-border bg-card px-3 text-sm placeholder:text-muted focus:border-brand focus:outline-none", className)} {...p} />;
});

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<"textarea">>(function Textarea({ className, ...p }, ref) {
  return <textarea ref={ref} className={cn("min-h-24 w-full rounded-xl border border-border bg-card p-3 text-sm placeholder:text-muted focus:border-brand focus:outline-none", className)} {...p} />;
});

export const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<"select">>(function Select({ className, ...p }, ref) {
  return <select ref={ref} className={cn("h-11 w-full rounded-xl border border-border bg-card px-3 text-sm focus:border-brand focus:outline-none", className)} {...p} />;
});

export function Field({ label, error, children, hint }: { label: string; error?: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block space-y-1.5 text-sm">
      <span className="font-medium">{label}</span>
      {children}
      {hint && !error && <span className="block text-xs text-muted">{hint}</span>}
      {error && <span role="alert" className="block text-xs text-danger">{error}</span>}
    </label>
  );
}

export function Badge({ tone = "info", className, ...p }: React.ComponentProps<"span"> & { tone?: "info" | "ok" | "warn" | "danger" }) {
  const tones = { info: "bg-soft text-brand", ok: "bg-ok/15 text-ok", warn: "bg-warn/15 text-warn", danger: "bg-danger/15 text-danger" };
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", tones[tone], className)} {...p} />;
}

export function Alert({ tone = "info", className, ...p }: React.ComponentProps<"div"> & { tone?: "info" | "warn" | "danger" | "ok" }) {
  const tones = { info: "border-brand/30 bg-soft", warn: "border-warn/40 bg-warn/10", danger: "border-danger/50 bg-danger/10", ok: "border-ok/40 bg-ok/10" };
  return <div role={tone === "danger" ? "alert" : "status"} className={cn("rounded-xl border p-3 text-sm leading-relaxed", tones[tone], className)} {...p} />;
}

export function Spinner() {
  return <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />;
}
