create table if not exists mowing_workers (
    id text primary key,
    name text not null,
    area text not null,
    phone text not null default '',
    approval_status text not null default 'approved',
    service_note text not null default '',
    available boolean not null default true,
    created_at timestamptz not null default now()
);

alter table if exists mowing_workers add column if not exists phone text not null default '';
alter table if exists mowing_workers add column if not exists approval_status text not null default 'approved';
alter table if exists mowing_workers add column if not exists service_note text not null default '';

create table if not exists mowing_orders (
    id text primary key,
    user_name text not null,
    phone text not null,
    address text not null,
    service_type text not null,
    requested_time text not null,
    lawn_size text not null,
    condition_note text not null,
    customer_note text not null default '',
    status text not null,
    quoted_price numeric(10, 2),
    price_note text not null default '',
    assigned_worker_id text references mowing_workers(id),
    updated_at timestamptz not null default now(),
    photos_json jsonb not null default '[]'::jsonb,
    activity_json jsonb not null default '[]'::jsonb
);

create index if not exists idx_mowing_orders_status on mowing_orders(status);
create index if not exists idx_mowing_orders_updated_at on mowing_orders(updated_at desc);
