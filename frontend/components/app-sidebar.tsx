"use client"

import { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import { 
  GalleryVerticalEnd, 
  LayoutDashboard,
  Bot, 
  ListTree, 
  Database, 
  Activity, 
  Terminal,
  Sliders
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  SidebarRail,
} from "@/components/ui/sidebar"
import Link from "next/link"
import { cn } from "@/lib/utils"

const data = {
  groups: [
    {
      title: "Launchpad",
      items: [
        {
          title: "Dashboard",
          url: "/",
          icon: LayoutDashboard,
        },
        {
          title: "Metric Builder",
          url: "/metric-builder",
          icon: Bot,
        },
      ],
    },
    {
      title: "Configuration",
      items: [
        {
          title: "Pipelines",
          url: "/pipelines",
          icon: ListTree,
        },
        {
          title: "Metrics",
          url: "/metrics",
          icon: Sliders,
        },
        {
          title: "Datasets",
          url: "/datasets",
          icon: Database,
        },
      ],
    },
    {
      title: "Diagnostics",
      items: [
        {
          title: "Evaluations",
          url: "/evaluations",
          icon: Activity,
        },
        {
          title: "Runtimes",
          url: "/runtimes",
          icon: Terminal,
        },
      ],
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()
  const [isOnline, setIsOnline] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const checkStatus = async () => {
      try {
        const res = await fetch(`${baseUrl}/healthz`, { method: "GET", cache: "no-store" });
        setIsOnline(res.ok);
      } catch {
        setIsOnline(false);
      } finally {
        setChecking(false);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-3">
          <div className="flex h-6 w-6 items-center justify-center rounded-[2px] bg-primary text-primary-foreground">
            <GalleryVerticalEnd className="size-4" />
          </div>
          <span className="font-semibold text-sm group-data-[collapsible=icon]:hidden">EvalPlatform</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {data.groups.map((group) => (
          <SidebarGroup key={group.title}>
            <SidebarGroupLabel className="font-mono text-[9px] uppercase tracking-wider select-none group-data-[collapsible=icon]:opacity-0 transition-opacity">
              {group.title}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const isActive = pathname === item.url || (item.url !== "/" && pathname.startsWith(item.url));
                  return (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton 
                        isActive={isActive}
                        className={cn(
                          "transition-all duration-150 rounded-[2px] relative group/btn h-9",
                          isActive 
                            ? "font-semibold text-foreground bg-muted/40 border-l-[3px] border-primary pl-2.5" 
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/10 opacity-70 hover:opacity-100"
                        )}
                        render={
                          <Link href={item.url} className="flex items-center gap-2 w-full">
                            <item.icon className={cn(
                              "h-4 w-4 transition-transform group-hover/btn:translate-x-0.5",
                              isActive ? "text-primary animate-pulse" : ""
                            )} />
                            <span className="group-data-[collapsible=icon]:hidden">{item.title}</span>
                          </Link>
                        }
                      />
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="border-t border-border/40 p-3 group-data-[collapsible=icon]:p-2 shrink-0">
        <div className="flex items-center gap-2 overflow-hidden text-xs font-mono justify-center group-data-[collapsible=icon]:justify-center">
          <div className="relative flex h-2 w-2 shrink-0">
            <span className={cn(
              "absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping",
              isOnline ? "bg-emerald-400" : "bg-rose-400"
            )} />
            <span className={cn(
              "relative inline-flex h-2 w-2 rounded-full",
              isOnline ? "bg-emerald-500" : "bg-rose-500"
            )} />
          </div>
          <span className="text-[10px] text-muted-foreground group-data-[collapsible=icon]:hidden truncate select-none">
            {checking ? "CHECKING..." : isOnline ? "SYS ONLINE" : "SYS OFFLINE"}
          </span>
        </div>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
