-- Supabase schema for the Basel cold-chain manufacturing risk prototype.
-- Apply in the Supabase SQL Editor. Open-data and demo material records are
-- readable by the dashboard; all writes should use a server-side service key.

create extension if not exists pgcrypto;

create table if not exists public.data_sources (
    id text primary key,
    name text not null,
    url text not null,
    source_kind text not null check (source_kind in ('meteo_current', 'json', 'html')),
    description text,
    enabled boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists public.fetch_runs (
    id uuid primary key default gen_random_uuid(),
    source_id text not null references public.data_sources(id),
    fetched_at timestamptz not null,
    http_status integer check (http_status between 100 and 599),
    request_ok boolean not null,
    rate_limited boolean not null default false,
    retry_after text,
    response_bytes bigint check (response_bytes >= 0),
    error text,
    source_last_modified timestamptz,
    raw_payload jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.observations (
    id bigint generated always as identity primary key,
    source_id text not null references public.data_sources(id),
    fetch_run_id uuid references public.fetch_runs(id) on delete set null,
    observation_key text not null,
    observed_at timestamptz,
    station_id text,
    station_name text,
    metric text not null,
    value numeric,
    unit text,
    dimensions jsonb not null default '{}'::jsonb,
    raw_record jsonb not null default '{}'::jsonb,
    ingested_at timestamptz not null default now(),
    unique (source_id, observation_key, metric)
);

create table if not exists public.materials (
    id uuid primary key default gen_random_uuid(),
    material_code text not null unique,
    name text not null,
    description text,
    storage_min_c numeric not null default 2,
    storage_max_c numeric not null default 8,
    criticality text not null default 'high'
        check (criticality in ('low', 'medium', 'high', 'critical')),
    lead_time_hours numeric check (lead_time_hours is null or lead_time_hours >= 0),
    next_required_at timestamptz,
    created_at timestamptz not null default now(),
    check (storage_min_c <= storage_max_c)
);

create table if not exists public.material_lots (
    id uuid primary key default gen_random_uuid(),
    material_id uuid not null references public.materials(id),
    lot_code text not null,
    quantity numeric not null check (quantity >= 0),
    quantity_unit text not null default 'units',
    expires_at timestamptz,
    status text not null default 'in_transit'
        check (status in ('in_transit', 'available', 'reserved', 'quarantine', 'depleted')),
    location text,
    temperature_min_c numeric not null default 2,
    temperature_max_c numeric not null default 8,
    created_at timestamptz not null default now(),
    unique (material_id, lot_code),
    check (temperature_min_c <= temperature_max_c)
);

create table if not exists public.shipments (
    id uuid primary key default gen_random_uuid(),
    material_id uuid not null references public.materials(id),
    lot_id uuid references public.material_lots(id),
    origin text,
    destination text,
    transport_mode text,
    route_name text,
    status text not null default 'planned'
        check (status in ('planned', 'in_transit', 'delivered', 'delayed', 'cancelled')),
    departed_at timestamptz,
    expected_arrival_at timestamptz,
    actual_arrival_at timestamptz,
    route_details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.manufacturing_decisions (
    id uuid primary key default gen_random_uuid(),
    material_id uuid not null references public.materials(id),
    lot_id uuid references public.material_lots(id),
    shipment_id uuid references public.shipments(id),
    action text not null check (action in ('normal', 'buffer', 'expedite', 'reroute', 'quarantine')),
    risk_score numeric not null check (risk_score between 0 and 100),
    risk_level text not null check (risk_level in ('low', 'moderate', 'high', 'critical')),
    rationale text not null,
    evidence jsonb not null default '[]'::jsonb,
    decided_at timestamptz not null default now(),
    valid_until timestamptz,
    supersedes_id uuid references public.manufacturing_decisions(id),
    created_at timestamptz not null default now()
);

create index if not exists fetch_runs_source_fetched_idx
    on public.fetch_runs (source_id, fetched_at desc);
create index if not exists observations_metric_time_idx
    on public.observations (metric, observed_at desc);
create index if not exists observations_source_station_time_idx
    on public.observations (source_id, station_id, observed_at desc);
create index if not exists lots_material_status_idx
    on public.material_lots (material_id, status);
create index if not exists shipments_arrival_idx
    on public.shipments (expected_arrival_at);
create index if not exists decisions_latest_idx
    on public.manufacturing_decisions (material_id, decided_at desc);

insert into public.data_sources (id, name, url, source_kind, description) values
    ('meteoswiss_basel_temperature', 'MeteoSwiss Basel/Binningen temperature',
     'https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/VQHA80.csv',
     'meteo_current', 'Current air temperature for station BAS; tre200s0 in °C.'),
    ('basel_dataset_100006', 'Basel-Stadt dataset 100006 records',
     'https://data.bs.ch/api/explore/v2.1/catalog/datasets/100006/records/',
     'json', 'Basel motor traffic counts. Collector requests the latest 10 records.'),
    ('basel_dataset_100089', 'Basel-Stadt dataset 100089 records',
     'https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records/',
     'json', 'Rhine water level and discharge. Collector requests the latest 10 records.'),
    ('port_pegel_current', 'Port of Switzerland current water levels',
     'https://port-of-switzerland.ch/hafenservice/pegel/',
     'html', 'Parsed page headings, visible text, and tables.'),
    ('port_pegel_forecast', 'Port of Switzerland water-level forecast',
     'https://port-of-switzerland.ch/hafenservice/pegel/vorhersage-tabelle/',
     'html', 'Parsed page headings, visible text, and tables.')
on conflict (id) do update set
    name = excluded.name,
    url = excluded.url,
    source_kind = excluded.source_kind,
    description = excluded.description;

alter table public.data_sources enable row level security;
alter table public.fetch_runs enable row level security;
alter table public.observations enable row level security;
alter table public.materials enable row level security;
alter table public.material_lots enable row level security;
alter table public.shipments enable row level security;
alter table public.manufacturing_decisions enable row level security;

drop policy if exists "Dashboard can read data sources" on public.data_sources;
create policy "Dashboard can read data sources" on public.data_sources
    for select to anon, authenticated using (true);
drop policy if exists "Dashboard can read fetch runs" on public.fetch_runs;
create policy "Dashboard can read fetch runs" on public.fetch_runs
    for select to anon, authenticated using (true);
drop policy if exists "Dashboard can read observations" on public.observations;
create policy "Dashboard can read observations" on public.observations
    for select to anon, authenticated using (true);
drop policy if exists "Dashboard can read materials" on public.materials;
create policy "Dashboard can read materials" on public.materials
    for select to anon, authenticated using (true);
drop policy if exists "Dashboard can read material lots" on public.material_lots;
create policy "Dashboard can read material lots" on public.material_lots
    for select to anon, authenticated using (true);
drop policy if exists "Dashboard can read shipments" on public.shipments;
create policy "Dashboard can read shipments" on public.shipments
    for select to anon, authenticated using (true);
drop policy if exists "Dashboard can read decisions" on public.manufacturing_decisions;
create policy "Dashboard can read decisions" on public.manufacturing_decisions
    for select to anon, authenticated using (true);

grant select on public.data_sources, public.fetch_runs, public.observations,
    public.materials, public.material_lots, public.shipments,
    public.manufacturing_decisions to anon, authenticated;
grant all on public.data_sources, public.fetch_runs, public.observations,
    public.materials, public.material_lots, public.shipments,
    public.manufacturing_decisions to service_role;
grant usage, select on sequence public.observations_id_seq to service_role;
