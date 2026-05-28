import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";

import { Button, Field, Input } from "@/shared/ui";
import { useLogin } from "../api/useLogin";
import { loginSchema, type LoginInput } from "../model/auth.schema";

export function SignInForm({ onSuccess }: { onSuccess: () => void }) {
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const login = useLogin();

  const onSubmit = form.handleSubmit(async (input) => {
    await login.mutateAsync(input);
    onSuccess();
  });

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <Field label="Email" required error={form.formState.errors.email?.message}>
        <Input type="email" autoComplete="email" placeholder="you@company.com" {...form.register("email")} />
      </Field>

      <Field label="Password" required error={form.formState.errors.password?.message}>
        <Input type="password" autoComplete="current-password" placeholder="••••••••" {...form.register("password")} />
      </Field>

      {login.error && (
        <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
          {login.error.message}
        </p>
      )}

      <Button type="submit" size="lg" disabled={login.isPending} className="mt-2 w-full">
        {login.isPending ? "Signing in…" : "Sign in"}
        {!login.isPending && <ArrowRight size={14} strokeWidth={1.8} />}
      </Button>

      <p className="text-center text-[11px] text-ink-mute">
        Tip · use any email and an 8+ char password. Try
        <code className="mx-1 rounded-[3px] border border-canvas-rule bg-canvas-inset px-1 py-0.5">fail@yuno</code>
        to see an error.
      </p>
    </form>
  );
}
