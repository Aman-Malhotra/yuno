import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";

import { Button, Field, Input } from "@/shared/ui";
import { useSignup } from "../api/useSignup";
import { signupSchema, type SignupInput } from "../model/auth.schema";

export function SignUpForm({ onSuccess }: { onSuccess: () => void }) {
  const form = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "" },
  });

  const signup = useSignup();

  const onSubmit = form.handleSubmit(async (input) => {
    await signup.mutateAsync(input);
    onSuccess();
  });

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <Field label="Full name" required error={form.formState.errors.name?.message}>
        <Input autoComplete="name" placeholder="Aman Malhotra" {...form.register("name")} />
      </Field>

      <Field label="Email" required error={form.formState.errors.email?.message}>
        <Input type="email" autoComplete="email" placeholder="you@company.com" {...form.register("email")} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field
          label="Password"
          hint="8+ chars, 1 uppercase, 1 digit"
          required
          error={form.formState.errors.password?.message}
        >
          <Input type="password" autoComplete="new-password" placeholder="••••••••" {...form.register("password")} />
        </Field>

        <Field label="Confirm" required error={form.formState.errors.confirmPassword?.message}>
          <Input
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            {...form.register("confirmPassword")}
          />
        </Field>
      </div>

      {signup.error && (
        <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
          {signup.error.message}
        </p>
      )}

      <Button type="submit" size="lg" disabled={signup.isPending} className="mt-2 w-full">
        {signup.isPending ? "Creating account…" : "Create account"}
        {!signup.isPending && <ArrowRight size={14} strokeWidth={1.8} />}
      </Button>

      <p className="text-center text-[11px] text-ink-mute">By creating an account you agree to the dev-trial terms.</p>
    </form>
  );
}
