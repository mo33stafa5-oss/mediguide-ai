-- MediGuide AI core schema. Every patient-owned table has RLS keyed on auth.uid().
create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto with schema extensions;

create type public.app_role as enum ('patient', 'admin', 'medical_reviewer');
create type public.account_status as enum ('active', 'suspended');
create type public.document_type as enum ('xray', 'ecg', 'lab', 'prescription', 'general');
create type public.document_status as enum ('uploaded', 'processing', 'analyzed', 'needs_review', 'failed');
create type public.knowledge_status as enum ('pending', 'approved', 'rejected', 'archived');

create or replace function public.set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

-- ---------- profiles ----------
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '' check (char_length(full_name) <= 200),
  role public.app_role not null default 'patient',
  status public.account_status not null default 'active',
  locale text not null default 'ar' check (locale in ('ar','en')),
  consent_terms_at timestamptz,
  consent_ai_processing_at timestamptz,   -- informed consent before sending data to Gemini
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_profiles_updated before update on public.profiles for each row execute function public.set_updated_at();

create or replace function public.is_admin() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin' and status = 'active')
$$;
create or replace function public.is_reviewer() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role in ('admin','medical_reviewer') and status = 'active')
$$;

-- new auth user -> profile (role is ALWAYS patient here; promotion is admin/service-role only)
create or replace function public.handle_new_user() returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, full_name, locale, consent_terms_at)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name',''),
          case when new.raw_user_meta_data->>'locale' = 'en' then 'en' else 'ar' end,
          case when (new.raw_user_meta_data->>'consent_terms') = 'true' then now() end);
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();

-- block privilege escalation: users may not change role/status/their own consent-less fields via the API
create or replace function public.protect_profile_fields() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is not null and not public.is_admin() then
    if new.role is distinct from old.role or new.status is distinct from old.status then
      raise exception 'role/status can only be changed by an administrator' using errcode = '42501';
    end if;
  end if;
  return new;
end $$;
create trigger trg_protect_profile before update on public.profiles for each row execute function public.protect_profile_fields();

-- ---------- medical profile ----------
create table public.user_medical_profiles (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  date_of_birth date check (date_of_birth <= current_date),
  sex text check (sex in ('male','female')),
  height_cm numeric(5,1) check (height_cm between 30 and 260),
  weight_kg numeric(5,1) check (weight_kg between 2 and 500),
  blood_type text check (blood_type in ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
  allergies text[] not null default '{}',
  chronic_conditions text[] not null default '{}',
  family_history text not null default '' check (char_length(family_history) <= 2000),
  smoker boolean,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger trg_ump_updated before update on public.user_medical_profiles for each row execute function public.set_updated_at();

-- ---------- chat ----------
create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null default 'New conversation' check (char_length(title) <= 200),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index conversations_user_idx on public.conversations (user_id, updated_at desc);
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null check (role in ('user','assistant')),
  content text not null check (char_length(content) <= 20000),
  sources jsonb not null default '[]',
  is_emergency boolean not null default false,
  created_at timestamptz not null default now()
);
create index messages_conv_idx on public.messages (conversation_id, created_at);

-- ---------- documents ----------
create table public.medical_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  doc_type public.document_type not null,
  detected_type public.document_type,
  original_name text not null check (char_length(original_name) <= 255),
  storage_bucket text not null,
  storage_path text not null unique,
  mime_type text not null,
  size_bytes bigint not null check (size_bytes > 0 and size_bytes <= 20971520),
  sha256 text,
  status public.document_status not null default 'uploaded',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index medical_documents_user_idx on public.medical_documents (user_id, created_at desc);
create trigger trg_docs_updated before update on public.medical_documents for each row execute function public.set_updated_at();

create table public.medical_analysis_reports (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.medical_documents(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  report_type public.document_type not null,
  ocr_engine text,
  raw_text text,
  extracted jsonb not null default '{}',       -- structured values, each with confidence
  warnings text[] not null default '{}',
  user_confirmed boolean not null default false,
  created_at timestamptz not null default now()
);
create index reports_doc_idx on public.medical_analysis_reports (document_id);
create index reports_user_idx on public.medical_analysis_reports (user_id, created_at desc);

create table public.heart_risk_assessments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  inputs jsonb not null,
  prediction int not null check (prediction in (0,1)),
  score numeric(5,4) not null check (score between 0 and 1),
  model_version text not null,
  created_at timestamptz not null default now()
);
create index hra_user_idx on public.heart_risk_assessments (user_id, created_at desc);

create table public.prescriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  document_id uuid references public.medical_documents(id) on delete set null,
  prescribed_on date,
  prescriber text,
  confirmed_by_user boolean not null default false,
  review jsonb not null default '{}',          -- interaction/duplicate/allergy warnings + sources
  created_at timestamptz not null default now()
);
create index prescriptions_user_idx on public.prescriptions (user_id, created_at desc);

create table public.medication_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  prescription_id uuid references public.prescriptions(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 200),
  dosage text,
  frequency text,
  duration text,
  ocr_confidence numeric(4,3) check (ocr_confidence between 0 and 1),
  verified boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create index medrec_user_idx on public.medication_records (user_id, active);

-- ---------- knowledge base (RAG) ----------
create table public.medical_knowledge (
  id uuid primary key default gen_random_uuid(),
  source_name text not null,
  source_url text not null check (source_url ~ '^https?://'),
  title text not null,
  language text not null default 'en' check (language in ('ar','en')),
  published_on date,
  last_reviewed_on date,
  content text not null check (char_length(content) between 20 and 8000),
  chunk_index int not null default 0,
  embedding extensions.vector(768),
  status public.knowledge_status not null default 'pending',
  approved_by uuid references public.profiles(id),
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);
create index knowledge_status_idx on public.medical_knowledge (status);
create index knowledge_embedding_idx on public.medical_knowledge using hnsw (embedding extensions.vector_cosine_ops);

create or replace function public.match_medical_knowledge(query_embedding extensions.vector(768), match_count int default 5, min_similarity float default 0.45)
returns table (id uuid, source_name text, source_url text, title text, published_on date, last_reviewed_on date, content text, similarity float)
language sql stable security invoker set search_path = public, extensions as $$
  select k.id, k.source_name, k.source_url, k.title, k.published_on, k.last_reviewed_on, k.content,
         1 - (k.embedding <=> query_embedding) as similarity
  from public.medical_knowledge k
  where k.status = 'approved' and k.embedding is not null
    and 1 - (k.embedding <=> query_embedding) >= min_similarity
  order by k.embedding <=> query_embedding
  limit least(match_count, 20)
$$;

-- ---------- audit + settings ----------
create table public.audit_logs (
  id bigint generated always as identity primary key,
  actor_id uuid,
  action text not null,
  entity text,
  entity_id text,
  metadata jsonb not null default '{}',   -- never contains medical content
  created_at timestamptz not null default now()
);
create index audit_actor_idx on public.audit_logs (actor_id, created_at desc);
create table public.system_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
insert into public.system_settings (key, value) values
  ('retention_days_documents', '365'), ('max_upload_mb', '20'), ('emergency_number_eg', '"123"');

-- ================= RLS =================
alter table public.profiles enable row level security;
alter table public.user_medical_profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.medical_documents enable row level security;
alter table public.medical_analysis_reports enable row level security;
alter table public.heart_risk_assessments enable row level security;
alter table public.prescriptions enable row level security;
alter table public.medication_records enable row level security;
alter table public.medical_knowledge enable row level security;
alter table public.audit_logs enable row level security;
alter table public.system_settings enable row level security;

create policy profiles_select on public.profiles for select to authenticated using (id = auth.uid() or public.is_admin());
create policy profiles_update_own on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
create policy profiles_update_admin on public.profiles for update to authenticated using (public.is_admin()) with check (public.is_admin());
-- no INSERT policy (trigger does it) and no DELETE policy (deletion goes through the backend / auth.users cascade)

-- Owner-only tables (admins deliberately get NO access to private medical rows)
do $$
declare t text;
begin
  foreach t in array array['user_medical_profiles','conversations','messages','medical_documents',
                           'medical_analysis_reports','heart_risk_assessments','prescriptions','medication_records']
  loop
    execute format('create policy %I_owner_select on public.%I for select to authenticated using (user_id = auth.uid())', t, t);
    execute format('create policy %I_owner_insert on public.%I for insert to authenticated with check (user_id = auth.uid())', t, t);
    execute format('create policy %I_owner_update on public.%I for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid())', t, t);
    execute format('create policy %I_owner_delete on public.%I for delete to authenticated using (user_id = auth.uid())', t, t);
  end loop;
end $$;

-- child rows must reference a parent owned by the same user (prevents cross-tenant linking)
create or replace function public.assert_same_owner() returns trigger language plpgsql security definer set search_path = public as $$
declare parent_owner uuid; j jsonb := to_jsonb(new);
begin
  if tg_table_name = 'messages' then
    select user_id into parent_owner from public.conversations where id = (j->>'conversation_id')::uuid;
  elsif tg_table_name = 'medical_analysis_reports' then
    select user_id into parent_owner from public.medical_documents where id = (j->>'document_id')::uuid;
  elsif tg_table_name = 'medication_records' then
    if j->>'prescription_id' is null then return new; end if;
    select user_id into parent_owner from public.prescriptions where id = (j->>'prescription_id')::uuid;
  elsif tg_table_name = 'prescriptions' then
    if j->>'document_id' is null then return new; end if;
    select user_id into parent_owner from public.medical_documents where id = (j->>'document_id')::uuid;
  else
    return new;
  end if;
  if parent_owner is distinct from new.user_id then raise exception 'parent row belongs to another user' using errcode = '42501'; end if;
  return new;
end $$;
create trigger trg_owner_messages before insert or update on public.messages for each row execute function public.assert_same_owner();
create trigger trg_owner_reports before insert or update on public.medical_analysis_reports for each row execute function public.assert_same_owner();
create trigger trg_owner_medrec before insert or update on public.medication_records for each row execute function public.assert_same_owner();
create trigger trg_owner_rx before insert or update on public.prescriptions for each row execute function public.assert_same_owner();

-- knowledge: patients read approved only; reviewers/admins manage
create policy knowledge_read_approved on public.medical_knowledge for select to authenticated using (status = 'approved' or public.is_reviewer());
create policy knowledge_reviewer_insert on public.medical_knowledge for insert to authenticated with check (public.is_reviewer());
create policy knowledge_reviewer_update on public.medical_knowledge for update to authenticated using (public.is_reviewer()) with check (public.is_reviewer());
create policy knowledge_admin_delete on public.medical_knowledge for delete to authenticated using (public.is_admin());

create policy audit_admin_read on public.audit_logs for select to authenticated using (public.is_admin());
create policy audit_self_insert on public.audit_logs for insert to authenticated with check (actor_id = auth.uid());
create policy settings_read on public.system_settings for select to authenticated using (true);
create policy settings_admin_write on public.system_settings for all to authenticated using (public.is_admin()) with check (public.is_admin());

grant usage on schema public to authenticated, service_role;
grant select, insert, update, delete on all tables in schema public to authenticated;
revoke all on all tables in schema public from anon;
grant usage, select on all sequences in schema public to authenticated;
grant execute on function public.match_medical_knowledge to authenticated;
