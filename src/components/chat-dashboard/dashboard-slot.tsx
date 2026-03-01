import type { PropsWithChildren, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type DashboardSlotId = "left" | "center" | "right" | "chat";

type DashboardSlotProps = PropsWithChildren<{
  id: DashboardSlotId;
  className?: string;
  label?: string;
  before?: ReactNode;
  after?: ReactNode;
}>;

export function DashboardSlot({ id, className, label, before, after, children }: DashboardSlotProps) {
  return (
    <section
      data-dashboard-slot={id}
      aria-label={label}
      className={cn("dashboard-slot", className)}
    >
      {before}
      {children}
      {after}
    </section>
  );
}
