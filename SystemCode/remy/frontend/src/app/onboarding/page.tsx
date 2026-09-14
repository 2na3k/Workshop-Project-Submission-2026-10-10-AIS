import type { Metadata } from "next";
import Screen from "@/components/screen";
import PreferencesForm from "@/components/preferences-form";

export const metadata: Metadata = {
  title: "Your preferences · Remy",
  description: "Tell Remy about your diet and the cuisines you enjoy.",
};

export default function Page() {
  return (
    <Screen
      width="wide"
      title="What do you eat?"
      subtitle="This shapes every recipe Remy suggests. You can change it later."
    >
      <PreferencesForm />
    </Screen>
  );
}
