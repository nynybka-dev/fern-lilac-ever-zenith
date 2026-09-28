import { createFileRoute } from "@tanstack/react-router";
import { RegistryApp } from "@/components/registry-app";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <RegistryApp />;
}
