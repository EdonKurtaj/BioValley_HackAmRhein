-- Preserve the original schema and collector tables; keep factory records server-side.
-- Optional factory tables may be absent in collector-only Supabase installations.
begin;

do $migration$
declare
    factory_table text;
    dashboard_policy text;
begin
    for factory_table, dashboard_policy in
        select * from (values
            ('materials', 'Dashboard can read materials'),
            ('material_lots', 'Dashboard can read material lots'),
            ('shipments', 'Dashboard can read shipments'),
            ('manufacturing_decisions', 'Dashboard can read decisions')
        ) as factory_access(table_name, policy_name)
    loop
        if to_regclass(format('public.%I', factory_table)) is not null then
            execute format('drop policy if exists %I on public.%I', dashboard_policy, factory_table);
            execute format('revoke all on public.%I from anon, authenticated', factory_table);
        end if;
    end loop;
end;
$migration$;

commit;
