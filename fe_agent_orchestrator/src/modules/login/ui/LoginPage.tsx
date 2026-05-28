import { useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";

import { AuthBranding } from "./AuthBranding";
import { ModeTabs } from "./ModeTabs";
import { SignInForm } from "./SignInForm";
import { SignUpForm } from "./SignUpForm";
import { loginCopy, type AuthMode } from "../config/login.config";

export function LoginPage() {
  const [mode, setMode] = useState<AuthMode>("signin");
  const navigate = useNavigate();
  const search = useSearch({ strict: false }) as { redirect?: string };

  const handleSuccess = () => {
    void navigate({ to: search.redirect ?? "/" });
  };

  const isSignin = mode === "signin";

  return (
    <div className="min-h-screen w-full bg-canvas">
      <div className="mx-auto grid min-h-screen w-full max-w-[1280px] grid-cols-1 lg:grid-cols-[5fr_6fr]">
        <AuthBranding />

        <main className="relative flex items-center justify-center px-6 py-12 lg:px-16">
          <div className="w-full max-w-sm">
            <header className="flex flex-col gap-2">
              <h2 className="text-2xl font-light text-ink">
                {isSignin ? loginCopy.signinTitle : loginCopy.signupTitle}
              </h2>
              <p className="text-[13px] text-ink-dim">
                {isSignin ? loginCopy.signinSubtitle : loginCopy.signupSubtitle}
              </p>
            </header>

            <div className="mt-6">
              <ModeTabs mode={mode} onChange={setMode} />
            </div>

            <div className="mt-8">
              {isSignin ? <SignInForm onSuccess={handleSuccess} /> : <SignUpForm onSuccess={handleSuccess} />}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
