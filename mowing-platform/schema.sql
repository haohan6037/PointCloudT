create table if not exists mowing_workers (
    id text primary key,
    name text not null,
    email text not null default '',
    area text not null,
    phone text not null default '',
    approval_status text not null default 'approved',
    service_note text not null default '',
    available boolean not null default true,
    created_at timestamptz not null default now()
);

alter table if exists mowing_workers add column if not exists phone text not null default '';
alter table if exists mowing_workers add column if not exists email text not null default '';
alter table if exists mowing_workers add column if not exists approval_status text not null default 'approved';
alter table if exists mowing_workers add column if not exists service_note text not null default '';
alter table if exists mowing_workers add column if not exists lat double precision;
alter table if exists mowing_workers add column if not exists lng double precision;

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
    priority_level text not null default 'normal',
    ops_tag text not null default '',
    quoted_price numeric(10, 2),
    price_note text not null default '',
    assigned_worker_id text references mowing_workers(id),
    actual_amount numeric(10, 2),
    payment_status text not null default 'unpaid',
    payment_method text not null default '',
    payment_received_at timestamptz,
    payment_note text not null default '',
    settlement_status text not null default 'pending',
    completion_note text not null default '',
    review_note text not null default '',
    exception_type text not null default '',
    exception_note text not null default '',
    exception_resolution text not null default '',
    platform_share numeric(10, 2),
    worker_payout numeric(10, 2),
    settled_at timestamptz,
    updated_at timestamptz not null default now(),
    photos_json jsonb not null default '[]'::jsonb,
    activity_json jsonb not null default '[]'::jsonb
);

alter table if exists mowing_orders add column if not exists actual_amount numeric(10, 2);
alter table if exists mowing_orders add column if not exists payment_status text not null default 'unpaid';
alter table if exists mowing_orders add column if not exists payment_method text not null default '';
alter table if exists mowing_orders add column if not exists payment_received_at timestamptz;
alter table if exists mowing_orders add column if not exists payment_note text not null default '';
alter table if exists mowing_orders add column if not exists settlement_status text not null default 'pending';
alter table if exists mowing_orders add column if not exists completion_note text not null default '';
alter table if exists mowing_orders add column if not exists review_note text not null default '';
alter table if exists mowing_orders add column if not exists priority_level text not null default 'normal';
alter table if exists mowing_orders add column if not exists ops_tag text not null default '';
alter table if exists mowing_orders add column if not exists exception_type text not null default '';
alter table if exists mowing_orders add column if not exists exception_note text not null default '';
alter table if exists mowing_orders add column if not exists exception_resolution text not null default '';
alter table if exists mowing_orders add column if not exists platform_share numeric(10, 2);
alter table if exists mowing_orders add column if not exists worker_payout numeric(10, 2);
alter table if exists mowing_orders add column if not exists settled_at timestamptz;
alter table if exists mowing_orders add column if not exists internal_note text not null default '';

create index if not exists idx_mowing_orders_status on mowing_orders(status);
create index if not exists idx_mowing_orders_updated_at on mowing_orders(updated_at desc);
create index if not exists idx_mowing_workers_email on mowing_workers(email);

create table if not exists app_users (
    email text primary key,
    clerk_user_id text not null default '',
    display_name text not null default '',
    role text not null default 'customer',
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table if exists app_users add column if not exists clerk_user_id text not null default '';
alter table if exists app_users add column if not exists display_name text not null default '';
alter table if exists app_users add column if not exists role text not null default 'customer';
alter table if exists app_users add column if not exists status text not null default 'active';

create index if not exists idx_app_users_role on app_users(role);

create table if not exists mqtt_messages (
    id bigserial primary key,
    topic text not null,
    payload text not null,
    payload_json jsonb,
    robot_id text not null default '',
    message_type text not null default '',
    source text not null default 'mqtt',
    received_at timestamptz not null default now()
);

alter table if exists mqtt_messages add column if not exists robot_id text not null default '';
alter table if exists mqtt_messages add column if not exists message_type text not null default '';

create index if not exists idx_mqtt_messages_received_at on mqtt_messages(received_at desc);
create index if not exists idx_mqtt_messages_topic on mqtt_messages(topic);
create index if not exists idx_mqtt_messages_robot_id on mqtt_messages(robot_id);
create index if not exists idx_mqtt_messages_message_type on mqtt_messages(message_type);
