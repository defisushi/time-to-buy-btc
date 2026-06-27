import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ReactNode } from "react";

interface ChartShellProps {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export default function ChartShell({ title, children, footer }: ChartShellProps) {
  return (
    <Card className="border-slate-700/50 bg-slate-800/40">
      <CardHeader className="pb-2">
        <CardTitle className="text-base text-slate-100">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full">{children}</div>
        {footer ? <div className="mt-3 text-xs text-slate-500">{footer}</div> : null}
      </CardContent>
    </Card>
  );
}

export function ChartEmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900/50 px-4 text-center text-sm text-slate-400">
      {message}
    </div>
  );
}
