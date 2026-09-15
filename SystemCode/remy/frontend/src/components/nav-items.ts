import { Compass, Heart, Sliders } from "@/components/icons";

export const NAV = [
  { href: "/", label: "Discover", Icon: Compass },
  { href: "/saved", label: "Saved meals", Icon: Heart },
  { href: "/preferences", label: "Your preferences", Icon: Sliders },
] as const;
