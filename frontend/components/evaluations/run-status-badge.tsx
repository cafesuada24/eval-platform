import { Badge } from "@/components/ui/badge";
import { AssertionStatus } from "@/lib/api/evaluations";
import { cn } from "@/lib/utils";

interface RunStatusBadgeProps {
  status: AssertionStatus | string;
  className?: string;
}

export function RunStatusBadge({ status, className }: RunStatusBadgeProps) {
  // If we receive the enum or a string representing the status
  const normalizedStatus =
    typeof status === "string" ? status.toUpperCase() : AssertionStatus[status];

  switch (normalizedStatus) {
    case "PASS":
    case AssertionStatus[AssertionStatus.PASS]:
      return (
        <Badge
          variant="outline"
          className={cn(
            "bg-emerald-500/10 text-emerald-600 border-emerald-500/20 font-medium",
            className
          )}
        >
          Pass
        </Badge>
      );
    case "WARNING":
    case AssertionStatus[AssertionStatus.WARNING]:
      return (
        <Badge
          variant="outline"
          className={cn(
            "bg-amber-500/10 text-amber-600 border-amber-500/20 font-medium",
            className
          )}
        >
          Warning
        </Badge>
      );
    case "FAIL":
    case AssertionStatus[AssertionStatus.FAIL]:
      return (
        <Badge
          variant="outline"
          className={cn(
            "bg-rose-500/10 text-rose-600 border-rose-500/20 font-medium",
            className
          )}
        >
          Fail
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className={cn("font-medium", className)}>
          Unknown
        </Badge>
      );
  }
}
