-- AIAC 2.0 Unified Database Schema
-- Merged from create_table.sql and original agent schema

-- =====================================================================
-- PART 1: CORE SCHEMA (Reference create_table.sql)
-- =====================================================================

CREATE TABLE IF NOT EXISTS public.alpha_pnl (
	id serial4 NOT NULL,
	alpha_id int4 NULL,
	trade_date date NOT NULL,
	pnl numeric(12, 6) NULL,
	cumulative_pnl numeric(12, 6) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT alpha_pnl_alpha_id_trade_date_key UNIQUE (alpha_id, trade_date),
	CONSTRAINT alpha_pnl_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.brain_auth_tokens (
	id int4 DEFAULT 1 NOT NULL,
	email varchar(255) NULL,
	jwt_token text NOT NULL,
	last_auth_time timestamp NOT NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT brain_auth_tokens_pkey PRIMARY KEY (id)
);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TABLE IF NOT EXISTS public.datasets (
	id serial4 NOT NULL,
	dataset_id varchar(100) NOT NULL,
	region varchar(10) NOT NULL,
	universe varchar(50) NOT NULL,
	"name" varchar(200) NOT NULL,
	category varchar(100) NULL,
	subcategory varchar(100) NULL,
	description text NULL,
	coverage numeric(5, 4) NULL,
	value_score int4 NULL,
	user_count int4 NULL,
	alpha_count int4 NULL,
	field_count int4 NULL,
	pyramid_multiplier numeric(3, 2) NULL,
	delay int4 DEFAULT 1 NULL,
	is_active bool DEFAULT true NULL,
	mining_weight float DEFAULT 1.0,  -- Added for Agent prioritization
    alpha_success_count int4 DEFAULT 0, -- Added for Agent stats
    alpha_fail_count int4 DEFAULT 0,    -- Added for Agent stats
	last_synced_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT datasets_dataset_id_region_delay_universe_key UNIQUE (dataset_id, region, delay, universe),
	CONSTRAINT datasets_pkey PRIMARY KEY (id)
);

DROP TRIGGER IF EXISTS update_datasets_updated_at ON public.datasets;
create trigger update_datasets_updated_at before update on public.datasets for each row execute function update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.generation_tasks (
	id serial4 NOT NULL,
	task_id varchar(50) NOT NULL,
	task_type varchar(50) NOT NULL,
	config jsonb NULL,
	status varchar(20) DEFAULT 'pending'::character varying NULL,
	progress int4 DEFAULT 0 NULL,
	total_items int4 NULL,
	completed_items int4 DEFAULT 0 NULL,
	"result" jsonb NULL,
	error_message text NULL,
	started_at timestamp NULL,
	completed_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT generation_tasks_pkey PRIMARY KEY (id),
	CONSTRAINT generation_tasks_task_id_key UNIQUE (task_id)
);

CREATE TABLE IF NOT EXISTS public.llm_providers (
	id serial4 NOT NULL,
	"name" varchar(100) NOT NULL,
	model_name varchar(200) NOT NULL,
	api_key_encrypted text NULL,
	base_url varchar(500) NULL,
	max_tokens int4 DEFAULT 4096 NULL,
	temperature numeric(3, 2) DEFAULT 0.7 NULL,
	is_active bool DEFAULT true NULL,
	is_default bool DEFAULT false NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT llm_providers_name_key UNIQUE (name),
	CONSTRAINT llm_providers_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.neutralizations (
	id serial4 NOT NULL,
	code varchar(50) NOT NULL,
	description text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT neutralizations_code_key UNIQUE (code),
	CONSTRAINT neutralizations_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.operation_logs (
	id serial4 NOT NULL,
	operation_type varchar(100) NOT NULL,
	entity_type varchar(100) NULL,
	entity_id int4 NULL,
	details jsonb NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT operation_logs_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.operator_blacklist (
	id serial4 NOT NULL,
	operator_name varchar(100) NOT NULL,
	error_message text NULL,
	first_seen_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	hit_count int4 DEFAULT 1 NULL,
	is_active bool DEFAULT true NULL,
	CONSTRAINT operator_blacklist_operator_name_key UNIQUE (operator_name),
	CONSTRAINT operator_blacklist_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_operator_blacklist_active ON public.operator_blacklist USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_operator_blacklist_name ON public.operator_blacklist USING btree (operator_name);

CREATE TABLE IF NOT EXISTS public.operators (
	id serial4 NOT NULL,
	"name" varchar(100) NOT NULL,
	category varchar(100) NULL,
	description text NULL,
	definition text NULL,
	"scope" _text NULL,
	"level" varchar(50) NULL,
	syntax text NULL,
	param_count int4 DEFAULT 0 NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT operators_name_key UNIQUE (name),
	CONSTRAINT operators_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.pyramid_multipliers (
	id serial4 NOT NULL,
	category varchar(100) NOT NULL,
	region varchar(10) NOT NULL,
	delay int4 NOT NULL,
	multiplier numeric(3, 2) NOT NULL,
	last_synced_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT pyramid_multipliers_category_region_delay_key UNIQUE (category, region, delay),
	CONSTRAINT pyramid_multipliers_pkey PRIMARY KEY (id)
);

DROP TRIGGER IF EXISTS update_pyramid_multipliers_updated_at ON public.pyramid_multipliers;
create trigger update_pyramid_multipliers_updated_at before update on public.pyramid_multipliers for each row execute function update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.regions (
	id serial4 NOT NULL,
	code varchar(10) NOT NULL,
	"name" varchar(100) NOT NULL,
	description text NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT regions_code_key UNIQUE (code),
	CONSTRAINT regions_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.rl_states (
	id serial4 NOT NULL,
	state_key varchar(200) NOT NULL,
	state_type varchar(50) NOT NULL,
	q_value numeric(10, 6) DEFAULT 0.0 NULL,
	visit_count int4 DEFAULT 0 NULL,
	success_count int4 DEFAULT 0 NULL,
	meta_data jsonb NULL, -- Renamed from metadata to avoid reserved word conflict
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT rl_states_pkey PRIMARY KEY (id),
	CONSTRAINT rl_states_state_key_key UNIQUE (state_key)
);

CREATE TABLE IF NOT EXISTS public.system_configs (
	id serial4 NOT NULL,
	config_key varchar(100) NOT NULL,
	config_value text NULL,
	config_type varchar(50) NULL,
	description text NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT system_configs_config_key_key UNIQUE (config_key),
	CONSTRAINT system_configs_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.template_evaluations (
	id serial4 NOT NULL,
	template_id int4 NULL,
	evaluation_batch_id varchar(50) NULL,
	region varchar(10) NULL,
	universe varchar(50) NULL,
	delay int4 NULL,
	total_alphas int4 NULL,
	successful_alphas int4 NULL,
	avg_sharpe numeric(6, 4) NULL,
	avg_fitness numeric(6, 4) NULL,
	avg_turnover numeric(6, 4) NULL,
	best_sharpe numeric(6, 4) NULL,
	best_fitness numeric(6, 4) NULL,
	evaluation_score numeric(6, 4) NULL,
	evaluated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT template_evaluations_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.template_variables (
	id serial4 NOT NULL,
	template_id int4 NULL,
	variable_name varchar(100) NOT NULL,
	config_type varchar(50) NOT NULL,
	allowed_values jsonb NULL,
	default_value varchar(200) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT template_variables_pkey PRIMARY KEY (id),
	CONSTRAINT template_variables_template_id_variable_name_key UNIQUE (template_id, variable_name)
);

CREATE TABLE IF NOT EXISTS public.templates (
	id serial4 NOT NULL,
	"name" varchar(200) NOT NULL,
	description text NULL,
	"expression" text NOT NULL,
	alpha_type varchar(20) DEFAULT 'atom'::character varying NOT NULL,
	template_configurations jsonb NULL,
	recommended_region varchar(10) NULL,
	recommended_universe varchar(50) NULL,
	recommended_neutralization varchar(50) NULL,
	recommended_delay int4 DEFAULT 1 NULL,
	recommended_decay int4 DEFAULT 0 NULL,
	recommended_truncation numeric(5, 4) DEFAULT 0.08 NULL,
	success_rate numeric(5, 4) DEFAULT 0.0 NULL,
	total_generated int4 DEFAULT 0 NULL,
	total_submitted int4 DEFAULT 0 NULL,
	avg_sharpe numeric(6, 4) NULL,
	avg_fitness numeric(6, 4) NULL,
	composite_score numeric(6, 4) NULL,
	"source" varchar(50) NULL,
	source_alpha_id varchar(20) NULL,
	source_alpha_expression text NULL,
	source_alpha_region varchar(10) NULL,
	is_active bool DEFAULT true NULL,
	is_validated bool DEFAULT false NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT templates_pkey PRIMARY KEY (id)
);

DROP TRIGGER IF EXISTS update_templates_updated_at ON public.templates;
create trigger update_templates_updated_at before update on public.templates for each row execute function update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.wqb_credentials (
	id serial4 NOT NULL,
	username_encrypted text NOT NULL,
	password_encrypted text NOT NULL,
	is_active bool DEFAULT true NULL,
	last_used_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT wqb_credentials_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.alphas (
	id serial4 NOT NULL,
	alpha_id varchar(20) NULL,
	alpha_type varchar(20) DEFAULT 'REGULAR'::character varying NOT NULL,
	author varchar(50) NULL,
	"name" varchar(200) NULL,
	favorite bool DEFAULT false NULL,
	hidden bool DEFAULT false NULL,
	color varchar(20) NULL,
	category varchar(100) NULL,
	tags _text NULL,
	grade varchar(20) NULL,
	stage varchar(10) DEFAULT 'IS'::character varying NULL,
	status varchar(20) DEFAULT 'created'::character varying NULL,
	"expression" text NOT NULL,
	expression_hash varchar(64) NULL,
	expression_description text NULL,
	operator_count int4 NULL,
	template_id int4 NULL,
	generation_batch_id varchar(50) NULL,
	seed_alpha_id varchar(20) NULL,
	instrument_type varchar(20) DEFAULT 'EQUITY'::character varying NULL,
	region varchar(10) NOT NULL,
	universe varchar(50) NOT NULL,
	dataset_id varchar(50) NULL,
	delay int4 DEFAULT 1 NULL,
	decay int4 DEFAULT 0 NULL,
	neutralization varchar(50) DEFAULT 'NONE'::character varying NULL,
	truncation numeric(5, 4) DEFAULT 0.08 NULL,
	pasteurization varchar(10) DEFAULT 'ON'::character varying NULL,
	unit_handling varchar(20) DEFAULT 'VERIFY'::character varying NULL,
	nan_handling varchar(10) DEFAULT 'ON'::character varying NULL,
	max_trade varchar(10) DEFAULT 'OFF'::character varying NULL,
	"language" varchar(20) DEFAULT 'FASTEXPR'::character varying NULL,
	visualization bool DEFAULT false NULL,
	backtest_start_date date NULL,
	backtest_end_date date NULL,
	settings_json jsonb NULL,
	is_pnl int8 NULL,
	is_book_size int8 NULL,
	is_sharpe numeric(6, 4) NULL,
	is_fitness numeric(6, 4) NULL,
	is_turnover numeric(6, 4) NULL,
	is_returns numeric(6, 4) NULL,
	is_margin numeric(10, 8) NULL,
	is_drawdown numeric(6, 4) NULL,
	is_long_count int4 NULL,
	is_short_count int4 NULL,
	is_start_date date NULL,
	is_self_correlation numeric(6, 4) NULL,
	is_prod_correlation numeric(6, 4) NULL,
	is_checks jsonb NULL,
	is_constrained_pnl int8 NULL,
	is_constrained_book_size int8 NULL,
	is_constrained_sharpe numeric(6, 4) NULL,
	is_constrained_fitness numeric(6, 4) NULL,
	is_constrained_turnover numeric(6, 4) NULL,
	is_constrained_returns numeric(6, 4) NULL,
	is_constrained_margin numeric(10, 8) NULL,
	is_constrained_drawdown numeric(6, 4) NULL,
	is_constrained_long_count int4 NULL,
	is_constrained_short_count int4 NULL,
	os_start_date date NULL,
	os_sharpe numeric(6, 4) NULL,
	os_fitness numeric(6, 4) NULL,
	os_turnover numeric(6, 4) NULL,
	os_returns numeric(6, 4) NULL,
	os_pnl int8 NULL,
	os_drawdown numeric(6, 4) NULL,
	os_is_sharpe_ratio numeric(6, 4) NULL,
	os_pre_close_sharpe_ratio numeric(6, 4) NULL,
	os_checks jsonb NULL,
	classifications jsonb NULL,
	competitions jsonb NULL,
	themes jsonb NULL,
	pyramids jsonb NULL,
	pyramid_themes jsonb NULL,
	team jsonb NULL,
	is_submittable bool DEFAULT false NULL,
	composite_score numeric(6, 4) NULL,
	core_metrics_score numeric(6, 4) NULL,
	risk_control_score numeric(6, 4) NULL,
	complexity_score numeric(6, 4) NULL,
	pnl_quality_score numeric(6, 4) NULL,
	self_corr_result jsonb NULL,
	prod_corr_result jsonb NULL,
	is_all_pass bool DEFAULT false NULL,
	self_corr numeric(6, 4) NULL,
	prod_corr numeric(6, 4) NULL,
	corr_checked_at timestamp NULL,
	error_message text NULL,
	date_created timestamp NULL,
	date_submitted timestamp NULL,
	date_modified timestamp NULL,
	simulated_at timestamp NULL,
	checked_at timestamp NULL,
	submitted_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    -- Agent Extensions
    task_id INTEGER NULL,
    trace_step_id INTEGER NULL,
    human_feedback VARCHAR(50) DEFAULT 'NONE',
    feedback_comment TEXT,
    metrics JSONB DEFAULT '{}'::jsonb,
    fields_used JSONB DEFAULT '[]'::jsonb,
    operators_used JSONB DEFAULT '[]'::jsonb,
    settings JSONB,
    checks JSONB,
    is_metrics JSONB,
    os_metrics JSONB,
    hypothesis TEXT,
    logic_explanation TEXT,
    config JSONB DEFAULT '{}'::jsonb,
	CONSTRAINT alphas_pkey PRIMARY KEY (id),
	CONSTRAINT alphas_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.templates(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alphas_alpha_id_unique ON public.alphas USING btree (alpha_id) WHERE (alpha_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_alphas_composite_score ON public.alphas USING btree (composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_alphas_is_all_pass ON public.alphas USING btree (is_all_pass) WHERE (is_all_pass = true);
CREATE INDEX IF NOT EXISTS idx_alphas_region_delay_universe ON public.alphas USING btree (region, delay, universe);
CREATE INDEX IF NOT EXISTS idx_alphas_status ON public.alphas USING btree (status);
CREATE INDEX IF NOT EXISTS idx_alphas_template_id ON public.alphas USING btree (template_id);

DROP TRIGGER IF EXISTS update_alphas_updated_at ON public.alphas;
create trigger update_alphas_updated_at before update on public.alphas for each row execute function update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.datafields (
	id serial4 NOT NULL,
	dataset_id int4 NULL,
	region varchar(10) NOT NULL,
	universe varchar(50) NOT NULL,
	delay int4 DEFAULT 1 NULL,
	field_id varchar(200) NOT NULL,
	field_name varchar(200) NOT NULL,
	field_type varchar(50) NULL,
	description text NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT datafields_dataset_id_field_id_key UNIQUE (dataset_id, field_id),
	CONSTRAINT datafields_pkey PRIMARY KEY (id),
	CONSTRAINT datafields_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id)
);
CREATE INDEX IF NOT EXISTS idx_datafields_region_delay_universe ON public.datafields USING btree (region, delay, universe);

CREATE TABLE IF NOT EXISTS public.rl_actions (
	id serial4 NOT NULL,
	state_id int4 NULL,
	action_type varchar(100) NULL,
	action_params jsonb NULL,
	reward numeric(10, 6) NULL,
	next_state_id int4 NULL,
	executed_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT rl_actions_pkey PRIMARY KEY (id),
	CONSTRAINT rl_actions_next_state_id_fkey FOREIGN KEY (next_state_id) REFERENCES public.rl_states(id),
	CONSTRAINT rl_actions_state_id_fkey FOREIGN KEY (state_id) REFERENCES public.rl_states(id)
);

CREATE TABLE IF NOT EXISTS public.template_datasets (
	id serial4 NOT NULL,
	template_id int4 NULL,
	dataset_id int4 NULL,
	priority int4 DEFAULT 0 NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT template_datasets_pkey PRIMARY KEY (id),
	CONSTRAINT template_datasets_template_id_dataset_id_key UNIQUE (template_id, dataset_id),
	CONSTRAINT template_datasets_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id)
);

CREATE TABLE IF NOT EXISTS public.universes (
	id serial4 NOT NULL,
	region_id int4 NULL,
	code varchar(50) NOT NULL,
	description text NULL,
	is_default bool DEFAULT false NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT universes_pkey PRIMARY KEY (id),
	CONSTRAINT universes_region_id_code_key UNIQUE (region_id, code),
	CONSTRAINT universes_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id)
);

-- =====================================================================
-- PART 2: AGENT SCHEMA EXTENSIONS
-- =====================================================================

-- 1. Mining Tasks (Maps partially to generation_tasks, but specialized)
CREATE TABLE IF NOT EXISTS mining_tasks (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(255) NOT NULL,
    region VARCHAR(50) NOT NULL,
    universe VARCHAR(100) NOT NULL,
    dataset_strategy VARCHAR(50) DEFAULT 'AUTO',
    target_datasets JSONB DEFAULT '[]'::jsonb,
    agent_mode VARCHAR(50) DEFAULT 'AUTONOMOUS',
    status VARCHAR(50) DEFAULT 'PENDING',
    daily_goal INTEGER DEFAULT 4,
    progress_current INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Trace Steps
CREATE TABLE IF NOT EXISTS trace_steps (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES mining_tasks(id) ON DELETE CASCADE,
    step_type VARCHAR(50) NOT NULL,
    step_order INTEGER NOT NULL,
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    duration_ms INTEGER,
    status VARCHAR(50) DEFAULT 'RUNNING',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Alpha Failures
CREATE TABLE IF NOT EXISTS alpha_failures (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES mining_tasks(id) ON DELETE SET NULL,
    trace_step_id INTEGER REFERENCES trace_steps(id) ON DELETE SET NULL,
    expression TEXT,
    error_type VARCHAR(100),
    error_message TEXT,
    raw_response TEXT,
    is_analyzed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Knowledge Entries
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id SERIAL PRIMARY KEY,
    entry_type VARCHAR(50) NOT NULL,
    pattern TEXT,
    description TEXT,
    meta_data JSONB DEFAULT '{}'::jsonb,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Operator Prefs (Compatibility)
CREATE TABLE IF NOT EXISTS operator_prefs (
    operator_name VARCHAR(100) PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_rate FLOAT DEFAULT 0.0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Foreign Key Links for Alphas (Agent)
ALTER TABLE public.alphas ADD CONSTRAINT alphas_task_id_fkey FOREIGN KEY (task_id) REFERENCES mining_tasks(id) ON DELETE SET NULL;
ALTER TABLE public.alphas ADD CONSTRAINT alphas_trace_step_id_fkey FOREIGN KEY (trace_step_id) REFERENCES trace_steps(id) ON DELETE SET NULL;

SELECT 'Unified Schema Loaded Successfully' as status;
