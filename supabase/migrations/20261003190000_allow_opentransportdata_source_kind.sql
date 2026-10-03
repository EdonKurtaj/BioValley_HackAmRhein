alter table public.data_sources
    drop constraint if exists data_sources_source_kind_check;

alter table public.data_sources
    add constraint data_sources_source_kind_check
    check (source_kind in ('meteo_current', 'json', 'html', 'opentransportdata'));
