import Sidebar from "@/components/sidebar";
import MobileBar from "@/components/mobile-bar";
import AuthButtons from "@/components/auth-buttons";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <MobileBar />
        <main className="flex-1 px-5 py-8 sm:px-8 lg:px-12 lg:py-10">
          <div className="mx-auto w-full max-w-4xl">
            <AuthButtons />
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
