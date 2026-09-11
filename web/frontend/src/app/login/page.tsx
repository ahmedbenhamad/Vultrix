"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Loader2, KeyRound } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { MFA_REQUIRED } from "@/lib/api";
import { Button, Card, Input } from "@/components/ui/primitives";

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [mfaStep, setMfaStep] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password, mfaStep ? otp : undefined);
      router.replace("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Login failed";
      if (msg === MFA_REQUIRED) {
        setMfaStep(true);
        setError("");
      } else {
        setError(msg === "MFA_REQUIRED" ? "Enter your authenticator code" : msg);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg">
            <ShieldAlert className="h-7 w-7 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-semibold text-white">Vultrix Console</h1>
          <p className="mt-1 text-sm text-slate-400">Sign in to the security operations console</p>
        </div>

        <Card className="p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="email">Email</label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                placeholder="admin@vultrix.local"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={mfaStep}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="password">Password</label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={mfaStep}
                required
              />
            </div>
            {mfaStep && (
              <div className="space-y-1.5">
                <label className="flex items-center gap-1.5 text-sm font-medium" htmlFor="otp">
                  <KeyRound className="h-3.5 w-3.5" /> Authenticator code
                </label>
                <Input
                  id="otp"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123456"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  autoFocus
                  required
                />
                <p className="text-xs text-muted-foreground">Enter the 6-digit code, or a recovery code.</p>
              </div>
            )}
            {error && (
              <div className="rounded-md bg-critical/10 px-3 py-2 text-sm text-critical">{error}</div>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {mfaStep ? "Verify" : "Sign in"}
            </Button>
          </form>
        </Card>
        <p className="mt-6 text-center text-xs text-slate-500">
          Default seeded admin: admin@vultrix.local / ChangeMe123!
        </p>
      </div>
    </div>
  );
}
