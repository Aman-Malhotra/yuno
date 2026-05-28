import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ className, ...rest }, ref) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-9 w-full rounded-md border border-canvas-ruleStrong bg-canvas-panel px-3 text-sm text-ink",
        "placeholder:text-ink-mute",
        "focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40",
        className,
      )}
      {...rest}
    />
  );
});
