"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth";
import { getPostAuthDestination } from "@/lib/auth-routing";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [kennitala, setKennitala] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (!/^\d{10}$/.test(kennitala)) {
      setError("Kennitala must be exactly 10 digits");
      return;
    }

    setIsLoading(true);

    try {
      const userData = await register(email, password, kennitala);
      router.push(getPostAuthDestination(userData));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center px-4 pt-14">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            Create an account
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Start sharing your projects today
          </p>
        </div>

        <div className="bg-white border border-border rounded-xl p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="label">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="label">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="At least 8 characters"
              />
            </div>

            <div>
              <label htmlFor="kennitala" className="label">Kennitala</label>
              <input
                id="kennitala"
                name="kennitala"
                type="text"
                required
                maxLength={10}
                value={kennitala}
                onChange={(e) => setKennitala(e.target.value.replace(/\D/g, ""))}
                className="input"
                placeholder="10 digits"
              />
            </div>

            <p className="text-xs text-muted-foreground">
              By creating an account, you agree to our{" "}
              <Link href="/privacy" className="text-accent hover:text-accent-hover transition-colors">
                Privacy Policy
              </Link>.
            </p>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary py-2.5"
            >
              {isLoading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-accent hover:text-accent-hover font-medium transition-colors">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
