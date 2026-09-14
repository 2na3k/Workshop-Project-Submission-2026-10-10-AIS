import type { Metadata } from "next";
import Screen from "@/components/screen";
import AuthForm from "@/components/auth-form";

export const metadata: Metadata = {
  title: "Sign in · Remy",
  description: "Sign in or create a Remy account.",
};

export default function Page() {
  return (
    <Screen
      title="Welcome to Remy"
      subtitle="Your kitchen assistant for what to cook, and what it costs."
    >
      <AuthForm />
    </Screen>
  );
}
