"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Account, ApiError, authAction, currentAccount } from "./api";

type Mode = "signin" | "recover" | "reset";

export default function AuthScreen({ mode = "signin" }: { mode?: Mode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(mode === "signin");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [requestId, setRequestId] = useState<string>();
  const [message, setMessage] = useState("");
  const [reset, setReset] = useState<{ uid: string; token: string } | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (mode === "reset") {
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      const uid = fragment.get("uid"), token = fragment.get("token");
      if (uid && token) {
        setReset({ uid, token });
        window.history.replaceState(null, "", window.location.pathname);
      }
    }
    if (mode !== "signin") return;
    let mounted = true;
    currentAccount().then((user) => { if (mounted) setAccount(user); })
      .catch(() => { if (mounted) setError("We couldn’t connect. Please refresh to try again."); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [mode]);

  useEffect(() => { if (error) errorRef.current?.focus(); }, [error]);

  useEffect(() => {
    if (!account) return;
    let lastSent = Date.now();
    const activity = () => {
      if (document.visibilityState !== "visible" || Date.now() - lastSent < 60_000) return;
      lastSent = Date.now();
      authAction("activity").catch(() => {
        setAccount(null);
        setError("Your session has expired. Sign in again.");
      });
    };
    window.addEventListener("pointerdown", activity);
    window.addEventListener("keydown", activity);
    return () => {
      window.removeEventListener("pointerdown", activity);
      window.removeEventListener("keydown", activity);
    };
  }, [account]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const { confirm_password: confirmation, ...values } =
      Object.fromEntries(new FormData(form).entries()) as Record<string, string>;
    setError(""); setMessage(""); setFieldErrors({}); setRequestId(undefined);
    if (values.new_password && values.new_password !== confirmation) {
      setError("The new passwords do not match."); return;
    }
    setBusy(true);
    try {
      if (account) {
        const result = await authAction("password/change", values);
        setAccount(null); setMessage(result.detail);
      } else if (mode === "recover") {
        const result = await authAction("password/recover", values);
        setMessage(result.detail);
      } else if (mode === "reset") {
        if (!reset) throw new Error("Open a valid password reset link from your email.");
        const result = await authAction("password/reset", { ...values, ...reset });
        setReset(null); setMessage(result.detail);
      } else {
        const result = await authAction("login", values);
        setAccount(result.user);
      }
      form.reset();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "We couldn’t connect. Please try again.");
      if (failure instanceof ApiError) {
        const allowed = new Set(["email", "password", "current_password", "new_password"]);
        setFieldErrors(Object.fromEntries(failure.fields
          .filter((field) => allowed.has(field.path.slice(1)))
          .map((field) => [field.path.slice(1), field.message])));
        setRequestId(failure.requestId);
      }
    } finally { setBusy(false); }
  }

  async function signOut() {
    setBusy(true); setError(""); setFieldErrors({}); setRequestId(undefined);
    try { await authAction("logout"); setAccount(null); setMessage("You’re signed out."); }
    catch { setError("We couldn’t sign you out. Please try again."); }
    finally { setBusy(false); }
  }

  if (loading) return <p role="status">Checking your session…</p>;
  const title = account ? `Welcome, ${account.display_name}.` :
    mode === "recover" ? "Forgot your password?" : mode === "reset" ? "Choose a new password." : "Sign in to your private workspace.";
  return (
    <section aria-labelledby="auth-title" className="auth-card">
      <p className="eyebrow">Your financial overview</p>
      <h1 id="auth-title">{title}</h1>
      {error && <p role="alert" tabIndex={-1} ref={errorRef} className="form-error">{error}
        {requestId && <span> Reference: {requestId}</span>}
      </p>}
      {message && <p role="status" className="form-success">{message}</p>}
      {account && <>
        <p>Signed in as {account.email}</p>
        <div className="notice"><h2>Your workspaces</h2>
          {account.workspaces.length ? <ul>{account.workspaces.map((workspace) =>
            <li key={workspace.id}>{workspace.name} · {workspace.role}</li>)}</ul> :
            <p>No workspace access is currently available. Contact your operator.</p>}
          <p>Account tracking and transactions are coming next.</p>
        </div>
        <button type="button" className="secondary" disabled={busy} onClick={signOut}>Sign out</button>
        <h2 className="password-heading">Change password</h2>
      </>}
      {mode === "recover" && <p>Enter your email. If an active account matches, we’ll send a link that expires in one hour.</p>}
      {mode === "reset" && !reset && !message && <p>Open the reset link from your email, or request a new one below.</p>}
      {(mode !== "reset" || reset) && <form onSubmit={submit} aria-busy={busy}>
        <fieldset disabled={busy}>
          <legend className="visually-hidden">{account ? "Change password" : title}</legend>
          {!account && mode !== "reset" && <label>Email address
            <input type="email" name="email" autoComplete="username" required maxLength={254}
              aria-invalid={!!fieldErrors.email} aria-describedby={fieldErrors.email ? "email-error" : undefined} />
            {fieldErrors.email && <span id="email-error" className="form-error">{fieldErrors.email}</span>}
          </label>}
          {!account && mode === "signin" && <label>Password
            <input type="password" name="password" autoComplete="current-password" required maxLength={1024}
              aria-invalid={!!fieldErrors.password} aria-describedby={fieldErrors.password ? "password-error" : undefined} />
            {fieldErrors.password && <span id="password-error" className="form-error">{fieldErrors.password}</span>}
          </label>}
          {account && <label>Current password
            <input type="password" name="current_password" autoComplete="current-password" required maxLength={1024}
              aria-invalid={!!fieldErrors.current_password} aria-describedby={fieldErrors.current_password ? "current-password-error" : undefined} />
            {fieldErrors.current_password && <span id="current-password-error" className="form-error">{fieldErrors.current_password}</span>}
          </label>}
          {(account || mode === "reset") && <>
            <p id="password-help">Use at least 12 characters. Avoid common passwords and personal details.</p>
            <label>New password
              <input type="password" name="new_password" autoComplete="new-password" required minLength={12} maxLength={1024}
                aria-invalid={!!fieldErrors.new_password}
                aria-describedby={fieldErrors.new_password ? "password-help new-password-error" : "password-help"} />
              {fieldErrors.new_password && <span id="new-password-error" className="form-error">{fieldErrors.new_password}</span>}
            </label>
            <label>Confirm new password
              <input type="password" name="confirm_password" autoComplete="new-password" required minLength={12} maxLength={1024} />
            </label>
          </>}
          <button type="submit">{busy ? "Please wait…" : account ? "Change password and sign out" :
            mode === "recover" ? "Send reset link" : mode === "reset" ? "Reset password" : "Sign in"}</button>
        </fieldset>
      </form>}
      {!account && <nav aria-label="Account help" className="account-links">
        {mode === "signin" ? <a href="/forgot-password">Forgot password?</a> : <a href="/">Back to sign in</a>}
        {mode === "reset" && <a href="/forgot-password">Request a new reset link</a>}
      </nav>}
      {!account && mode === "signin" && <p className="operator-help">Access is set up by your operator. Contact them if you don’t have an account.</p>}
    </section>
  );
}
