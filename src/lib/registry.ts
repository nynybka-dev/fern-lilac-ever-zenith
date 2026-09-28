import metaJson from "@/data/meta.json";

export type WebStatus = "live" | "dead" | "error" | "none";

export type KeptObject = {
  id: number;
  name: string;
  locality: string;
  address: string;
  phone: string;
  site: string;
  type: string;
  classified: boolean;
  regNum: string;
  regName: string;
  regStatus: string;
  regType: string;
  inn: string;
  ogrn: string;
  web: WebStatus;
  dupCount: number;
  mergedIds: number[];
};

export type RemovedObject = KeptObject & {
  removeKind: "duplicate" | "outdated";
  removeReason: string;
  canonicalId?: number;
};

export type Meta = {
  sourceFile: string;
  sourceCount: number;
  keptCount: number;
  removedCount: number;
  duplicateRemoved: number;
  outdatedRemoved: number;
  classifiedCount: number;
  unclassifiedCount: number;
  fgisActiveDump: number;
  fgisDumpDate: string;
  mintourismOperatingJan2026: number;
  classifiedOfficialMay2026: number;
  sitesChecked: number;
  sitesLive: number;
  typeBreakdown: { type: string; count: number }[];
  localityBreakdown: { locality: string; count: number }[];
  webBreakdown: Record<string, number>;
  updatedAt: string;
  methodology: string[];
};

export const meta = metaJson as Meta;

export const PAGE_SIZE = 24;

export const WEB_LABEL: Record<WebStatus, string> = {
  live: "Сайт открывается",
  dead: "Сайт не открывается",
  error: "Сайт с ошибкой",
  none: "Нет сайта",
};

export async function loadLists(): Promise<{ kept: KeptObject[]; removed: RemovedObject[] }> {
  const [kept, removed] = await Promise.all([
    fetch("/data/kept.json").then((r) => {
      if (!r.ok) throw new Error("Не удалось загрузить актуальный реестр");
      return r.json() as Promise<KeptObject[]>;
    }),
    fetch("/data/removed.json").then((r) => {
      if (!r.ok) throw new Error("Не удалось загрузить снятые записи");
      return r.json() as Promise<RemovedObject[]>;
    }),
  ]);
  return { kept, removed };
}

export function siteHref(site: string): string | null {
  const raw = site.trim();
  if (!raw) return null;
  if (/^https?:\/\//i.test(raw)) return raw.split(/[\s,;]/)[0];
  const first = raw.split(/[\s,;]/)[0];
  if (!first.includes(".")) return null;
  return `https://${first}`;
}

export function telHref(phone: string): string | null {
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 10) return null;
  const n = digits.startsWith("8") && digits.length === 11 ? `7${digits.slice(1)}` : digits;
  return `tel:+${n}`;
}

export function fgisHref(regNum: string): string | null {
  if (!regNum) return null;
  return `https://tourism.fsa.gov.ru/ru/resorts/hotels?search=${encodeURIComponent(regNum)}`;
}

export type Filters = {
  query: string;
  locality: string;
  type: string;
  classStatus: "all" | "yes" | "no";
  web: "all" | WebStatus;
  kind: "all" | "duplicate" | "outdated";
};

export const emptyFilters: Filters = {
  query: "",
  locality: "all",
  type: "all",
  classStatus: "all",
  web: "all",
  kind: "all",
};

function matchesQuery(row: KeptObject, q: string): boolean {
  if (!q) return true;
  const hay = `${row.name} ${row.address} ${row.phone} ${row.site} ${row.regNum} ${row.regName} ${row.inn}`.toLowerCase();
  return q
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((token) => hay.includes(token));
}

export function filterKept(rows: KeptObject[], f: Filters): KeptObject[] {
  return rows.filter((row) => {
    if (f.locality !== "all" && row.locality !== f.locality) return false;
    if (f.type !== "all" && row.type !== f.type) return false;
    if (f.classStatus === "yes" && !row.classified) return false;
    if (f.classStatus === "no" && row.classified) return false;
    if (f.web !== "all" && row.web !== f.web) return false;
    return matchesQuery(row, f.query);
  });
}

export function filterRemoved(rows: RemovedObject[], f: Filters): RemovedObject[] {
  return rows.filter((row) => {
    if (f.kind !== "all" && row.removeKind !== f.kind) return false;
    if (f.locality !== "all" && row.locality !== f.locality) return false;
    if (f.type !== "all" && row.type !== f.type) return false;
    return matchesQuery(row, f.query);
  });
}

export function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, "ru"));
}
