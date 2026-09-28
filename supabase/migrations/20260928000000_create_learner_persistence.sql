create table if not exists public.learner_states (
    learner_id varchar(64) primary key,
    state_json jsonb not null,
    state_version integer not null default 1,
    updated_at timestamptz not null
);

create table if not exists public.learning_events (
    id varchar(64) primary key,
    learner_id varchar(64) not null,
    plan_item_id varchar(64) not null,
    concept_ids jsonb not null,
    event_type varchar(32) not null,
    started_at timestamptz not null,
    active_seconds integer default 60,
    engagement_score double precision default 1.0,
    grading_result jsonb,
    created_at timestamptz not null
);

create index if not exists learning_events_learner_id_idx
    on public.learning_events (learner_id);

alter table public.learner_states enable row level security;
alter table public.learning_events enable row level security;