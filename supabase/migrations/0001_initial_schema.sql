-- ============================================================
-- cartwatch — initial schema
-- ============================================================

-- Enable UUID generation
create extension if not exists "uuid-ossp";
create extension if not exists "pg_trgm"; -- fuzzy matching for product reconciliation


-- ============================================================
-- SHARED / LOOKUP TABLES
-- ============================================================

create table units (
  id       uuid primary key default uuid_generate_v4(),
  symbol   text not null unique,   -- kg, L, piece
  name     text not null,          -- kilogram, litre, piece
  quantity text not null           -- mass | volume | count
);

create table categories (
  id        uuid primary key default uuid_generate_v4(),
  name      text not null unique,
  parent_id uuid references categories(id) on delete set null
);

create table store_chains (
  id          uuid primary key default uuid_generate_v4(),
  name        text not null unique,  -- REWE, Lidl, Aldi
  country     text not null default 'DE',
  logo_url    text
);

create table canonical_products (
  id              uuid primary key default uuid_generate_v4(),
  name            text not null,
  short_name      text not null,          -- milk, eggs, butter
  category_id     uuid references categories(id) on delete set null,
  unit_id         uuid references units(id) on delete restrict,
  barcode         text,                   -- EAN-13 if known
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index on canonical_products using gin (name gin_trgm_ops);
create index on canonical_products using gin (short_name gin_trgm_ops);


-- ============================================================
-- PRIVATE / PER-USER TABLES
-- ============================================================

create table stores (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  chain_id        uuid references store_chains(id) on delete set null,
  name            text not null,
  address         text,
  city            text,
  postal_code     text,
  country         text not null default 'DE',
  created_at      timestamptz not null default now()
);

create index on stores(user_id);

create table receipts (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  store_id        uuid references stores(id) on delete set null,
  purchased_at    timestamptz not null,
  currency        text not null default 'EUR',
  subtotal        numeric(10, 2),
  tax_total       numeric(10, 2),
  total           numeric(10, 2) not null,
  payment_method  text,
  created_at      timestamptz not null default now()
);

create index on receipts(user_id);
create index on receipts(purchased_at);

create table receipt_sources (
  id          uuid primary key default uuid_generate_v4(),
  receipt_id  uuid references receipts(id) on delete set null,
  user_id     uuid not null references auth.users(id) on delete cascade,
  source_type text not null,  -- 'email' | 'pdf' | 'manual'
  external_id text,           -- gmail message id, filename, etc.
  raw_text    text,           -- original extracted text
  created_at  timestamptz not null default now()
);

create index on receipt_sources(receipt_id);
create index on receipt_sources(user_id);

create table receipt_items (
  id                  uuid primary key default uuid_generate_v4(),
  receipt_id          uuid not null references receipts(id) on delete cascade,
  user_id             uuid not null references auth.users(id) on delete cascade,
  canonical_product_id uuid references canonical_products(id) on delete set null,
  raw_name            text not null,      -- original name from receipt
  short_name          text,               -- LLM-extracted short name
  quantity            numeric(10, 4) not null,
  unit_id             uuid references units(id) on delete restrict,
  unit_price          numeric(10, 4) not null,  -- in base SI unit
  total_price         numeric(10, 2) not null,
  discount            numeric(10, 2),
  tax_rate            numeric(5, 2),             -- 0.07 or 0.19
  created_at          timestamptz not null default now()
);

create index on receipt_items(receipt_id);
create index on receipt_items(user_id);
create index on receipt_items(canonical_product_id);


-- ============================================================
-- PRODUCT RECONCILIATION QUEUE
-- ============================================================

create type match_status as enum ('pending', 'confirmed', 'rejected');

create table product_matches (
  id                   uuid primary key default uuid_generate_v4(),
  receipt_item_id      uuid not null references receipt_items(id) on delete cascade,
  canonical_product_id uuid references canonical_products(id) on delete set null,
  confidence           numeric(4, 3) not null,   -- 0.000 to 1.000
  status               match_status not null default 'pending',
  matched_by           text,                     -- 'llm' | 'user' | 'rule'
  created_at           timestamptz not null default now(),
  reviewed_at          timestamptz
);

create index on product_matches(status);
create index on product_matches(receipt_item_id);


-- ============================================================
-- COMMUNITY PRICES
-- ============================================================

create table community_prices (
  id                   uuid primary key default uuid_generate_v4(),
  canonical_product_id uuid not null references canonical_products(id) on delete cascade,
  store_chain_id       uuid references store_chains(id) on delete set null,
  price_per_unit       numeric(10, 4) not null,  -- always in SI base unit
  unit_id              uuid not null references units(id) on delete restrict,
  currency             text not null default 'EUR',
  observed_at          timestamptz not null,
  created_at           timestamptz not null default now()
  -- no user_id — fully anonymized
);

create index on community_prices(canonical_product_id);
create index on community_prices(observed_at);
create index on community_prices(store_chain_id);


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table stores          enable row level security;
alter table receipts        enable row level security;
alter table receipt_sources enable row level security;
alter table receipt_items   enable row level security;
alter table product_matches enable row level security;

-- stores
create policy "users manage own stores"
  on stores for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- receipts
create policy "users manage own receipts"
  on receipts for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- receipt_sources
create policy "users manage own receipt sources"
  on receipt_sources for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- receipt_items
create policy "users manage own receipt items"
  on receipt_items for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- product_matches
create policy "users manage own matches"
  on product_matches for all
  using (
    auth.uid() = (
      select user_id from receipt_items
      where id = product_matches.receipt_item_id
    )
  );

-- shared tables: read-only for authenticated users
alter table canonical_products enable row level security;
alter table community_prices   enable row level security;
alter table units              enable row level security;
alter table categories         enable row level security;
alter table store_chains       enable row level security;

create policy "authenticated read canonical_products"
  on canonical_products for select
  using (auth.role() = 'authenticated');

create policy "authenticated read community_prices"
  on community_prices for select
  using (auth.role() = 'authenticated');

create policy "authenticated read units"
  on units for select
  using (auth.role() = 'authenticated');

create policy "authenticated read categories"
  on categories for select
  using (auth.role() = 'authenticated');

create policy "authenticated read store_chains"
  on store_chains for select
  using (auth.role() = 'authenticated');


-- ============================================================
-- SEED DATA
-- ============================================================

-- units (SI base)
insert into units (symbol, name, quantity) values
  ('kg',    'kilogram', 'mass'),
  ('L',     'litre',    'volume'),
  ('piece', 'piece',    'count'),
  ('m',     'metre',    'length');

-- categories (two-level hierarchy)
insert into categories (id, name, parent_id) values
  ('00000000-0000-0000-0000-000000000001', 'Food & Drink',       null),
  ('00000000-0000-0000-0000-000000000002', 'Household',          null),
  ('00000000-0000-0000-0000-000000000003', 'Personal Care',      null),
  ('00000000-0000-0000-0000-000000000004', 'Pet',                null),
  ('00000000-0000-0000-0000-000000000005', 'Other',              null),
  -- Food subcategories
  ('00000000-0000-0000-0000-000000000010', 'Dairy',              '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000011', 'Meat & Fish',        '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000012', 'Fruit & Vegetables', '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000013', 'Bakery',             '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000014', 'Beverages',          '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000015', 'Frozen',             '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000016', 'Pantry',             '00000000-0000-0000-0000-000000000001'),
  ('00000000-0000-0000-0000-000000000017', 'Snacks & Sweets',    '00000000-0000-0000-0000-000000000001'),
  -- Household subcategories
  ('00000000-0000-0000-0000-000000000020', 'Cleaning',           '00000000-0000-0000-0000-000000000002'),
  ('00000000-0000-0000-0000-000000000021', 'Laundry',            '00000000-0000-0000-0000-000000000002'),
  ('00000000-0000-0000-0000-000000000022', 'Paper & Disposable', '00000000-0000-0000-0000-000000000002');

-- store chains
insert into store_chains (name, country) values
  ('REWE',        'DE'),
  ('Lidl',        'DE'),
  ('Aldi Süd',    'DE'),
  ('Aldi Nord',   'DE'),
  ('Edeka',       'DE'),
  ('Penny',       'DE'),
  ('Netto',       'DE'),
  ('Kaufland',    'DE'),
  ('dm',          'DE'),
  ('Rossmann',    'DE'),
  ('Amazon',      'DE'),
  ('Other',       'DE');

-- grant permissions to service role (backend)
grant usage on schema public to service_role;
grant all on all tables in schema public to service_role;