import type { Metadata } from "next";
import Screen from "@/components/screen";
import PromptBox from "@/components/prompt-box";

export const metadata: Metadata = {
  title: "Ask Remy",
  description: "Describe a meal and Remy will suggest recipes.",
};

export default function Page() {
  return (
    <Screen
      width="wide"
      title="What are you in the mood for?"
      subtitle="Describe a meal, an ingredient you need to use up, or a budget."
    >
      <PromptBox />
    </Screen>
  );
}
