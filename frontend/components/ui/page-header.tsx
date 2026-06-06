import React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  preTitle?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  preTitle,
  title,
  description,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-border/40 shrink-0", className)}>
      <div className="space-y-1.5 max-w-3xl">
        {preTitle && (
          <p className="text-[10px] font-semibold text-primary uppercase tracking-widest font-mono">
            {preTitle}
          </p>
        )}
        <h1 className="text-3xl font-extrabold tracking-tighter text-foreground">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-muted-foreground leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-3 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
}
