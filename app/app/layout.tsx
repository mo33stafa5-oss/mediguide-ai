import { redirect } from "next/navigation";
import { AppShell, type Me } from "@/components/app-shell";
import { createClient } from "@/lib/supabase/server";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const { data: p } = await supabase.from("profiles").select("full_name,role,status,consent_ai_processing_at").eq("id", user.id).single();
  if (!p || p.status !== "active") redirect("/login");
  const me: Me = { id: user.id, email: user.email ?? "", full_name: p.full_name, role: p.role, consent_ai: !!p.consent_ai_processing_at };
  return <AppShell me={me}>{children}</AppShell>;
}
