begin;

-- Mobile client hardening after 0011.
-- - Allow authenticated users to remove their own registered notification device.
-- - Publish client-facing snapshot/portfolio/notification tables to Supabase Realtime.
-- This migration does not change model thresholds, signal logic, scheduler cadence,
-- Shadow state, or Python market/macro/model write semantics.

grant delete on public.notification_devices to authenticated;

DO $$
DECLARE
  table_name text;
  realtime_tables text[] := ARRAY[
    'market_snapshot',
    'decision_snapshot',
    'engine_health_snapshot',
    'model_validation_snapshot',
    'investment_accounts',
    'portfolio_transactions',
    'user_investment_settings',
    'financial_institutions',
    'investment_account_institutions',
    'push_provider_settings',
    'notification_devices',
    'notification_templates',
    'notification_messages',
    'notification_logs'
  ];
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    EXECUTE 'create publication supabase_realtime';
  END IF;

  FOREACH table_name IN ARRAY realtime_tables LOOP
    IF to_regclass(format('public.%I', table_name)) IS NOT NULL
       AND NOT EXISTS (
         SELECT 1
         FROM pg_publication_tables
         WHERE pubname = 'supabase_realtime'
           AND schemaname = 'public'
           AND tablename = table_name
       ) THEN
      EXECUTE format('alter publication supabase_realtime add table public.%I', table_name);
    END IF;
  END LOOP;
END;
$$;

commit;
