begin;

-- An authenticated user may permanently clear only the transaction history of
-- an investment account they own. General DELETE remains revoked so ordinary
-- clients cannot bypass append-only audit rules outside this explicit flow.
create or replace function public.reset_portfolio_transaction_history(
  p_account_id uuid,
  p_confirmation_phrase text
)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  authenticated_user_id uuid := auth.uid();
  deleted_count integer := 0;
begin
  if authenticated_user_id is null then
    raise exception 'Authentication is required.' using errcode = '42501';
  end if;

  if p_confirmation_phrase is distinct from 'PORTFÖYÜ SIFIRLA' then
    raise exception 'Portfolio reset confirmation is invalid.' using errcode = '22023';
  end if;

  if not exists (
    select 1
    from public.investment_accounts account
    where account.id = p_account_id
      and account.user_id = authenticated_user_id
      and account.is_active = true
  ) then
    raise exception 'Active investment account was not found for the authenticated user.'
      using errcode = '42501';
  end if;

  delete from public.portfolio_transactions transaction_row
  where transaction_row.account_id = p_account_id
    and transaction_row.user_id = authenticated_user_id;

  get diagnostics deleted_count = row_count;
  return deleted_count;
end;
$$;

revoke all on function public.reset_portfolio_transaction_history(uuid, text) from public;
revoke all on function public.reset_portfolio_transaction_history(uuid, text) from anon;
grant execute on function public.reset_portfolio_transaction_history(uuid, text) to authenticated;

comment on function public.reset_portfolio_transaction_history(uuid, text) is
  'Permanently deletes transaction and revision history for one active account owned by auth.uid(); preserves settings, market, model, decisions and engine state.';

commit;
