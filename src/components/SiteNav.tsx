import { NavLink } from "react-router-dom";
import { Activity, ChartCandlestick } from "lucide-react";

const links = [
  { to: "/", label: "Conviction", icon: Activity },
  { to: "/etf-options", label: "ETF + Options", icon: ChartCandlestick },
];

export default function SiteNav() {
  return (
    <nav className="flex gap-1 rounded-lg border border-slate-700/50 bg-slate-900/80 p-1">
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            [
              "flex min-h-[36px] flex-1 items-center justify-center gap-2 rounded-md px-3 text-sm font-semibold transition-colors",
              isActive ? "bg-slate-700 text-slate-50" : "text-slate-400 hover:bg-slate-800 hover:text-slate-200",
            ].join(" ")
          }
        >
          <Icon className="h-4 w-4" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

