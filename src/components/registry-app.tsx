import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Building2,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  MapPin,
  Phone,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  type Filters,
  type KeptObject,
  type Meta,
  type RemovedObject,
  type WebStatus,
  PAGE_SIZE,
  WEB_LABEL,
  emptyFilters,
  filterKept,
  filterRemoved,
  fgisHref,
  loadLists,
  meta,
  siteHref,
  telHref,
  uniqueSorted,
} from "@/lib/registry";

type Tab = "kept" | "removed" | "method";

const WEB_TONE: Record<WebStatus, "ok" | "bad" | "warn" | "neutral"> = {
  live: "ok",
  dead: "bad",
  error: "warn",
  none: "neutral",
};

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1.5">
      <span className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 w-full rounded-md bg-card px-3 text-sm text-foreground shadow-[var(--shadow-border)] outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ObjectDetail({
  row,
  onClose,
  removedView,
}: {
  row: KeptObject | RemovedObject;
  onClose: () => void;
  removedView: boolean;
}) {
  const href = siteHref(row.site);
  const tel = telHref(row.phone);
  const fgis = fgisHref(row.regNum);
  const removedRow = removedView ? (row as RemovedObject) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6">
      <button type="button" className="absolute inset-0 bg-ink/40" aria-label="Закрыть" onClick={onClose} />
      <div className="relative flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-t-xl bg-card shadow-[var(--shadow-border)] sm:rounded-xl">
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <p className="font-display text-xl font-medium leading-snug tracking-[-0.02em]">{row.name}</p>
            <p className="mt-1 text-sm text-muted-foreground">{row.locality}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Закрыть">
            <X className="size-5" />
          </Button>
        </div>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <div className="flex flex-wrap gap-2">
            {row.classified ? (
              <Badge tone="ok">Классификация подтверждена</Badge>
            ) : (
              <Badge tone="warn">Классификация не подтверждена</Badge>
            )}
            <Badge tone={WEB_TONE[row.web]}>{WEB_LABEL[row.web]}</Badge>
            {row.dupCount > 1 ? <Badge>Слито записей: {row.dupCount}</Badge> : null}
            {removedRow ? (
              <Badge tone={removedRow.removeKind === "duplicate" ? "neutral" : "bad"}>
                {removedRow.removeKind === "duplicate" ? "Дубль" : "Устаревший"}
              </Badge>
            ) : null}
          </div>
          {removedRow ? (
            <p className="rounded-md bg-surface-2 px-3.5 py-3 text-sm leading-relaxed">{removedRow.removeReason}</p>
          ) : null}
          <dl className="grid gap-4 text-sm">
            <div>
              <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">Адрес</dt>
              <dd className="mt-1 leading-relaxed">{row.address || "—"}</dd>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">Телефон</dt>
                <dd className="mt-1">
                  {tel ? (
                    <a className="text-primary underline-offset-2 hover:underline" href={tel}>
                      {row.phone}
                    </a>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">Сайт</dt>
                <dd className="mt-1 break-all">
                  {href ? (
                    <a className="text-primary underline-offset-2 hover:underline" href={href} target="_blank" rel="noreferrer">
                      {row.site}
                    </a>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">Тип</dt>
                <dd className="mt-1">{row.type || "—"}</dd>
              </div>
              <div>
                <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">Исходный №</dt>
                <dd className="mt-1 tabular-nums">{row.id}</dd>
              </div>
            </div>
            {row.regNum ? (
              <div className="rounded-md bg-surface-2 px-3.5 py-3">
                <p className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">ФГИС «Гостеприимство»</p>
                <p className="mt-1 font-medium">{row.regName || "Запись найдена"}</p>
                <p className="mt-1 font-mono text-xs tabular-nums">
                  {fgis ? (
                    <a className="text-primary underline-offset-2 hover:underline" href={fgis} target="_blank" rel="noreferrer">
                      {row.regNum}
                    </a>
                  ) : (
                    row.regNum
                  )}
                  {row.regStatus ? ` · ${row.regStatus}` : ""}
                </p>
                {row.inn ? <p className="mt-1 text-xs text-muted-foreground">ИНН {row.inn}</p> : null}
              </div>
            ) : null}
          </dl>
        </div>
      </div>
    </div>
  );
}

function Pager({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (p: number) => void }) {
  if (pages <= 1) {
    return <p className="text-sm text-muted-foreground tabular-nums">{total} записей</p>;
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground tabular-nums">
        {total} записей · стр. {page} из {pages}
      </p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          <ChevronLeft className="size-4" />
          Назад
        </Button>
        <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Дальше
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}

export function RegistryApp() {
  const [lists, setLists] = useState<{ kept: KeptObject[]; removed: RemovedObject[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("kept");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<KeptObject | RemovedObject | null>(null);

  useEffect(() => {
    let alive = true;
    loadLists()
      .then((d) => {
        if (alive) setLists(d);
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : "Ошибка загрузки");
      });
    return () => {
      alive = false;
    };
  }, []);

  if (error) {
    return (
      <Shell>
        <p className="px-4 py-16 text-center text-sm text-muted-foreground">{error}</p>
      </Shell>
    );
  }

  if (!lists) {
    return (
      <Shell>
        <p className="px-4 py-10 text-center text-sm text-muted-foreground">Загружаю 1699 актуальных записей…</p>
      </Shell>
    );
  }

  return (
    <LoadedApp
      kept={lists.kept}
      removed={lists.removed}
      tab={tab}
      setTab={setTab}
      filters={filters}
      setFilters={setFilters}
      page={page}
      setPage={setPage}
      open={open}
      setOpen={setOpen}
    />
  );
}

function Shell({ children }: { children?: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[0.6875rem] font-medium uppercase tracking-[0.18em] text-primary">Республика Дагестан</p>
              <h1 className="mt-2 max-w-xl font-display text-3xl font-medium leading-tight tracking-[-0.03em] sm:text-4xl">
                Реестр размещения
              </h1>
              <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">
                2125 исходных записей сверены с открытыми источниками 27 сентября 2026 года. Дубли объединены, устаревшие
                и агрегаторские объявления сняты.
              </p>
            </div>
            <a
              href="/reestr-dagestan-2026-09-27.xlsx"
              className="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
            >
              <Download className="size-4" />
              Скачать Excel
            </a>
          </div>
          <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-border sm:grid-cols-5">
            {[
              ["Было", String(meta.sourceCount)],
              ["Актуальных", String(meta.keptCount)],
              ["Дублей снято", String(meta.duplicateRemoved)],
              ["Устаревших", String(meta.outdatedRemoved)],
              ["ФГИС подтверждён", String(meta.classifiedCount)],
            ].map(([k, v]) => (
              <div key={k} className="bg-card px-4 py-4">
                <dt className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">{k}</dt>
                <dd className="mt-1 font-display text-2xl font-medium tabular-nums tracking-[-0.03em]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </header>
      {children}
    </div>
  );
}

function LoadedApp({
  kept,
  removed,
  tab,
  setTab,
  filters,
  setFilters,
  page,
  setPage,
  open,
  setOpen,
}: {
  kept: KeptObject[];
  removed: RemovedObject[];
  tab: Tab;
  setTab: (t: Tab) => void;
  filters: Filters;
  setFilters: (f: Filters | ((p: Filters) => Filters)) => void;
  page: number;
  setPage: (n: number) => void;
  open: KeptObject | RemovedObject | null;
  setOpen: (r: KeptObject | RemovedObject | null) => void;
}) {

  const localities = useMemo(
    () => uniqueSorted((tab === "removed" ? removed : kept).map((r) => r.locality)),
    [tab, kept, removed],
  );
  const types = useMemo(
    () => uniqueSorted((tab === "removed" ? removed : kept).map((r) => r.type)),
    [tab, kept, removed],
  );

  const keptRows = useMemo(() => filterKept(kept, filters), [kept, filters]);
  const removedRows = useMemo(() => filterRemoved(removed, filters), [removed, filters]);
  const rows = tab === "removed" ? removedRows : keptRows;
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, pages);
  const slice = rows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function patch(next: Partial<Filters>) {
    setFilters((f) => ({ ...f, ...next }));
    setPage(1);
  }

  return (
    <Shell>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-5 flex gap-1 rounded-lg bg-surface-2 p-1">
          {(
            [
              ["kept", "Актуальные"],
              ["removed", "Снятые"],
              ["method", "Методика"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                setTab(id);
                setPage(1);
              }}
              className={cn(
                "h-10 flex-1 rounded-md text-sm font-medium transition-colors duration-[var(--motion-quick)]",
                tab === id ? "bg-card text-foreground shadow-[var(--shadow-border)]" : "text-muted-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "method" ? (
          <MethodPanel meta={meta} />
        ) : (
          <>
            <div className="mb-5 grid gap-3 rounded-xl bg-card p-4 shadow-[var(--shadow-border)] sm:grid-cols-2 lg:grid-cols-5">
              <label className="flex min-w-0 flex-col gap-1.5 sm:col-span-2 lg:col-span-2">
                <span className="text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-subtle">Поиск</span>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
                  <Input
                    className="pl-10"
                    placeholder="Название, адрес, телефон, ИНН"
                    value={filters.query}
                    onChange={(e) => patch({ query: e.target.value })}
                  />
                </div>
              </label>
              <SelectField
                label="Населённый пункт"
                value={filters.locality}
                onChange={(v) => patch({ locality: v })}
                options={[{ value: "all", label: "Все" }, ...localities.map((l) => ({ value: l, label: l }))]}
              />
              <SelectField
                label="Тип"
                value={filters.type}
                onChange={(v) => patch({ type: v })}
                options={[{ value: "all", label: "Все" }, ...types.map((t) => ({ value: t, label: t }))]}
              />
              {tab === "kept" ? (
                <SelectField
                  label="Классификация"
                  value={filters.classStatus}
                  onChange={(v) => patch({ classStatus: v as Filters["classStatus"] })}
                  options={[
                    { value: "all", label: "Все" },
                    { value: "yes", label: "Подтверждена" },
                    { value: "no", label: "Не подтверждена" },
                  ]}
                />
              ) : (
                <SelectField
                  label="Причина снятия"
                  value={filters.kind}
                  onChange={(v) => patch({ kind: v as Filters["kind"] })}
                  options={[
                    { value: "all", label: "Все" },
                    { value: "duplicate", label: "Дубль" },
                    { value: "outdated", label: "Устаревший / не объект" },
                  ]}
                />
              )}
            </div>

            <div className="mb-4">
              <Pager page={safePage} pages={pages} total={rows.length} onPage={setPage} />
            </div>

            <div className="overflow-hidden rounded-xl bg-card shadow-[var(--shadow-border)]">
              <ul className="divide-y divide-border">
                {slice.length === 0 ? (
                  <li className="px-5 py-16 text-center text-sm text-muted-foreground">Ничего не найдено по текущим фильтрам.</li>
                ) : (
                  slice.map((row) => {
                    const href = siteHref(row.site);
                    const tel = telHref(row.phone);
                    const rem = tab === "removed" ? (row as RemovedObject) : null;
                    return (
                      <li key={`${tab}-${row.id}`}>
                        <button
                          type="button"
                          onClick={() => setOpen(row)}
                          className="flex w-full flex-col gap-2 px-4 py-4 text-left transition-colors duration-[var(--motion-quick)] hover:bg-surface-2/60 sm:px-5"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="font-medium leading-snug">{row.name}</p>
                              <p className="mt-1 flex items-start gap-1.5 text-sm text-muted-foreground">
                                <MapPin className="mt-0.5 size-3.5 shrink-0" />
                                <span>{row.address || row.locality}</span>
                              </p>
                            </div>
                            <div className="flex flex-wrap justify-end gap-1.5">
                              {row.classified ? <Badge tone="ok">ФГИС</Badge> : <Badge tone="warn">Без ФГИС</Badge>}
                              {rem ? (
                                <Badge tone={rem.removeKind === "duplicate" ? "neutral" : "bad"}>
                                  {rem.removeKind === "duplicate" ? "Дубль" : "Устаревший"}
                                </Badge>
                              ) : (
                                <Badge tone={WEB_TONE[row.web]}>{WEB_LABEL[row.web]}</Badge>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                            <span className="inline-flex items-center gap-1">
                              <Building2 className="size-3.5" />
                              {row.type || "Тип не указан"}
                            </span>
                            {tel ? (
                              <span className="inline-flex items-center gap-1">
                                <Phone className="size-3.5" />
                                {row.phone}
                              </span>
                            ) : null}
                            {href ? (
                              <span className="inline-flex items-center gap-1">
                                <ExternalLink className="size-3.5" />
                                сайт
                              </span>
                            ) : null}
                            {row.dupCount > 1 ? <span>слито {row.dupCount}</span> : null}
                          </div>
                          {rem ? <p className="text-xs leading-relaxed text-muted-foreground">{rem.removeReason}</p> : null}
                        </button>
                      </li>
                    );
                  })
                )}
              </ul>
            </div>

            <div className="mt-4">
              <Pager page={safePage} pages={pages} total={rows.length} onPage={setPage} />
            </div>
            <p className="mt-3 text-xs text-subtle">
              CSV:{" "}
              <a className="underline-offset-2 hover:underline" href="/reestr-aktualnyi.csv">
                актуальные
              </a>
              {" · "}
              <a className="underline-offset-2 hover:underline" href="/reestr-snyatye.csv">
                снятые
              </a>
            </p>
          </>
        )}
      </main>

      {open ? <ObjectDetail row={open} onClose={() => setOpen(null)} removedView={tab === "removed"} /> : null}
    </Shell>
  );
}

function MethodPanel({ meta }: { meta: Meta }) {
  const top = meta.localityBreakdown[0]?.count || 1;
  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-card p-5 shadow-[var(--shadow-border)] sm:p-7">
        <h2 className="font-display text-2xl font-medium tracking-[-0.02em]">Что сделано</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Исходный Excel содержал 2125 карточек — смесь гостиниц, баз, гостевых домов и объявлений с карт. Список сверен с
          выгрузкой ФГИС «Гостеприимство» от 23.09.2026 (479 действующих записей по Дагестану) и проверен по открытым
          источникам.
        </p>
        <ul className="mt-5 space-y-3 text-sm leading-relaxed">
          {meta.methodology.map((line) => (
            <li key={line} className="flex gap-3">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="grid gap-3 sm:grid-cols-2">
        <article className="rounded-xl bg-card p-5 shadow-[var(--shadow-border)]">
          <h3 className="font-display text-lg font-medium">Контекст рынка</h3>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li>Минтуризм РД, 02.01.2026: 892 коллективных средства размещения.</li>
            <li>Минтуризм РД, 19.05.2026: 403 объекта в Едином реестре классификации.</li>
            <li>Выгрузка ФГИС, 23.09.2026: 479 действующих записей.</li>
            <li>2ГИС: 1079 карточек по запросу «гостиница» в Махачкале и окрестностях — включая дубли и рекламу.</li>
            <li>
              Проверено сайтов: {meta.sitesChecked}, из них открываются {meta.sitesLive}.
            </li>
          </ul>
        </article>
        <article className="rounded-xl bg-card p-5 shadow-[var(--shadow-border)]">
          <h3 className="font-display text-lg font-medium">Важно</h3>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Отсутствие действующей классификации — не юридический факт нарушения. Нужно подтвердить, что объект реально
            принимает туристов и подпадает под требование о классификации. Записи без названия, телефона и сайта сняты как
            неидентифицируемые; сети домов с разными адресами оставлены раздельно.
          </p>
        </article>
      </section>
      <section className="rounded-xl bg-card p-5 shadow-[var(--shadow-border)]">
        <h3 className="font-display text-lg font-medium">Где сосредоточены актуальные объекты</h3>
        <ol className="mt-4 space-y-2">
          {meta.localityBreakdown.slice(0, 10).map((row) => (
            <li key={row.locality} className="flex items-center gap-3 text-sm">
              <span className="w-40 shrink-0 truncate sm:w-64">{row.locality}</span>
              <span className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                <span
                  className="block h-full rounded-full bg-primary"
                  style={{ width: `${Math.max(6, (row.count / top) * 100)}%` }}
                />
              </span>
              <span className="w-10 text-right tabular-nums text-muted-foreground">{row.count}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
