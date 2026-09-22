-- ============================================================
--  REFUND RADAR — SUPABASE DATABASE SETUP
-- ============================================================
--  Run this entire script once in:
--  Supabase Dashboard → SQL Editor → New query → Run
-- ============================================================

-- Clean slate (safe to re-run while you are setting up / testing)
drop table if exists evidence cascade;
drop table if exists refunds cascade;
drop table if exists transactions cascade;

-- ============================================================
-- 1. TRANSACTIONS
-- ============================================================
create table transactions (
    id                bigint generated always as identity primary key,
    transaction_id    text not null unique,
    order_id          text not null,
    platform          text not null,
    platform_logo     text not null default '🛒',
    transaction_type  text not null default 'purchase'
                        check (transaction_type in (
                            'purchase', 'subscription', 'bill_payment',
                            'food_order', 'ride', 'other'
                        )),
    amount            numeric(12,2) not null check (amount > 0),
    transaction_date  date not null,
    status            text not null default 'completed'
                        check (status in (
                            'completed', 'pending', 'cancelled', 'failed'
                        )),
    created_at        timestamptz not null default now()
);

create index idx_transactions_status on transactions (status);
create index idx_transactions_date   on transactions (transaction_date desc);

-- ============================================================
-- 2. REFUNDS
-- ============================================================
create table refunds (
    id              bigint generated always as identity primary key,
    transaction_id  text not null references transactions (transaction_id) on delete cascade,
    refund_amount   numeric(12,2) not null check (refund_amount > 0),
    reason          text not null,
    applied_date    date not null,
    due_date        date not null,
    status          text not null default 'pending'
                        check (status in (
                            'pending', 'processing', 'completed', 'rejected'
                        )),
    risk_score      integer not null default 0 check (risk_score between 0 and 100),
    risk_level      text not null default 'LOW' check (risk_level in ('LOW', 'MEDIUM', 'HIGH')),
    risk_reasons    jsonb not null default '[]'::jsonb,
    created_at      timestamptz not null default now(),

    constraint due_date_after_applied check (due_date >= applied_date)
);

create index idx_refunds_transaction_id on refunds (transaction_id);
create index idx_refunds_status         on refunds (status);
create index idx_refunds_due_date       on refunds (due_date);

-- ============================================================
-- 3. EVIDENCE
-- ============================================================
create table evidence (
    id              bigint generated always as identity primary key,
    transaction_id  text not null references transactions (transaction_id) on delete cascade,
    refund_id       bigint references refunds (id) on delete set null,
    file_name       text not null,
    file_path       text not null,
    file_type       text not null,
    uploaded_at     timestamptz not null default now(),
    created_at      timestamptz not null default now()
);

create index idx_evidence_transaction_id on evidence (transaction_id);
create index idx_evidence_refund_id      on evidence (refund_id);

-- ============================================================
-- 4. STORAGE BUCKET FOR EVIDENCE FILES
-- ============================================================
-- Creates a private bucket named "evidence" (JPG / PNG / PDF, 10 MB cap).
-- The backend uses the Supabase SECRET (service_role) key, which bypasses
-- storage RLS, so no public access policy is required.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'evidence',
    'evidence',
    false,
    10485760,
    array['image/jpeg', 'image/png', 'application/pdf']
)
on conflict (id) do nothing;

-- ============================================================
-- Done. Tables: transactions, refunds, evidence
-- Storage bucket: evidence
-- ============================================================
