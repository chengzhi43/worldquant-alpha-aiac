-- DROP SCHEMA public;

CREATE SCHEMA public AUTHORIZATION pg_database_owner;

COMMENT ON SCHEMA public IS 'standard public schema';

-- DROP SEQUENCE public.alpha_base_id_seq;

CREATE SEQUENCE public.alpha_base_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.alpha_failures_id_seq;

CREATE SEQUENCE public.alpha_failures_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.alpha_pnl_id_seq;

CREATE SEQUENCE public.alpha_pnl_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.alphas_id_seq;

CREATE SEQUENCE public.alphas_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.datafields_id_seq;

CREATE SEQUENCE public.datafields_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.datasets_id_seq;

CREATE SEQUENCE public.datasets_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.generation_tasks_id_seq;

CREATE SEQUENCE public.generation_tasks_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.knowledge_entries_id_seq;

CREATE SEQUENCE public.knowledge_entries_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.llm_providers_id_seq;

CREATE SEQUENCE public.llm_providers_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.mining_tasks_id_seq;

CREATE SEQUENCE public.mining_tasks_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.neutralizations_id_seq;

CREATE SEQUENCE public.neutralizations_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.operation_logs_id_seq;

CREATE SEQUENCE public.operation_logs_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.operator_blacklist_id_seq;

CREATE SEQUENCE public.operator_blacklist_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.operators_id_seq;

CREATE SEQUENCE public.operators_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pyramid_multipliers_id_seq;

CREATE SEQUENCE public.pyramid_multipliers_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.regions_id_seq;

CREATE SEQUENCE public.regions_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.rl_actions_id_seq;

CREATE SEQUENCE public.rl_actions_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.rl_states_id_seq;

CREATE SEQUENCE public.rl_states_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.system_configs_id_seq;

CREATE SEQUENCE public.system_configs_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.template_datasets_id_seq;

CREATE SEQUENCE public.template_datasets_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.template_evaluations_id_seq;

CREATE SEQUENCE public.template_evaluations_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.template_variables_id_seq;

CREATE SEQUENCE public.template_variables_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.templates_id_seq;

CREATE SEQUENCE public.templates_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.trace_steps_id_seq;

CREATE SEQUENCE public.trace_steps_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.universes_id_seq;

CREATE SEQUENCE public.universes_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.wqb_credentials_id_seq;

CREATE SEQUENCE public.wqb_credentials_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;-- public.alpha_pnl definition

-- Drop table

-- DROP TABLE public.alpha_pnl;

CREATE TABLE public.alpha_pnl (
	id serial4 NOT NULL,
	alpha_id int4 NULL,
	trade_date date NOT NULL,
	pnl numeric(12, 6) NULL,
	cumulative_pnl numeric(12, 6) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT alpha_pnl_alpha_id_trade_date_key UNIQUE (alpha_id, trade_date),
	CONSTRAINT alpha_pnl_pkey PRIMARY KEY (id)
);


-- public.brain_auth_tokens definition

-- Drop table

-- DROP TABLE public.brain_auth_tokens;

CREATE TABLE public.brain_auth_tokens (
	id int4 DEFAULT 1 NOT NULL,
	email varchar(255) NULL,
	jwt_token text NOT NULL,
	last_auth_time timestamp NOT NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT brain_auth_tokens_pkey PRIMARY KEY (id)
);


-- public.datasets definition

-- Drop table

-- DROP TABLE public.datasets;

CREATE TABLE public.datasets (
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
	mining_weight float8 DEFAULT 1.0 NULL,
	alpha_success_count int4 DEFAULT 0 NULL,
	alpha_fail_count int4 DEFAULT 0 NULL,
	last_synced_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	date_coverage float8 NULL,
	themes jsonb NULL,
	resources jsonb NULL,
	CONSTRAINT datasets_dataset_id_region_delay_universe_key UNIQUE (dataset_id, region, delay, universe),
	CONSTRAINT datasets_pkey PRIMARY KEY (id),
	CONSTRAINT uq_dataset_region_universe UNIQUE (dataset_id, region, universe)
);

-- Table Triggers

create trigger update_datasets_updated_at before
update
    on
    public.datasets for each row execute function update_updated_at_column();


-- public.generation_tasks definition

-- Drop table

-- DROP TABLE public.generation_tasks;

CREATE TABLE public.generation_tasks (
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


-- public.knowledge_entries definition

-- Drop table

-- DROP TABLE public.knowledge_entries;

CREATE TABLE public.knowledge_entries (
	id serial4 NOT NULL,
	entry_type varchar(50) NOT NULL,
	pattern text NULL,
	description text NULL,
	meta_data jsonb DEFAULT '{}'::jsonb NULL,
	usage_count int4 DEFAULT 0 NULL,
	is_active bool DEFAULT true NULL,
	created_by varchar(50) DEFAULT 'SYSTEM'::character varying NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT knowledge_entries_pkey PRIMARY KEY (id)
);


-- public.llm_providers definition

-- Drop table

-- DROP TABLE public.llm_providers;

CREATE TABLE public.llm_providers (
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


-- public.mining_tasks definition

-- Drop table

-- DROP TABLE public.mining_tasks;

CREATE TABLE public.mining_tasks (
	id serial4 NOT NULL,
	task_name varchar(255) NOT NULL,
	region varchar(50) NOT NULL,
	universe varchar(100) NOT NULL,
	dataset_strategy varchar(50) DEFAULT 'AUTO'::character varying NULL,
	target_datasets jsonb DEFAULT '[]'::jsonb NULL,
	agent_mode varchar(50) DEFAULT 'AUTONOMOUS'::character varying NULL,
	status varchar(50) DEFAULT 'PENDING'::character varying NULL,
	daily_goal int4 DEFAULT 4 NULL,
	progress_current int4 DEFAULT 0 NULL,
	config jsonb DEFAULT '{}'::jsonb NULL,
	created_at timestamptz DEFAULT now() NULL,
	updated_at timestamptz DEFAULT now() NULL,
	current_iteration int4 DEFAULT 0 NULL,
	max_iterations int4 DEFAULT 10 NULL,
	CONSTRAINT mining_tasks_pkey PRIMARY KEY (id)
);


-- public.neutralizations definition

-- Drop table

-- DROP TABLE public.neutralizations;

CREATE TABLE public.neutralizations (
	id serial4 NOT NULL,
	code varchar(50) NOT NULL,
	description text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT neutralizations_code_key UNIQUE (code),
	CONSTRAINT neutralizations_pkey PRIMARY KEY (id)
);


-- public.operation_logs definition

-- Drop table

-- DROP TABLE public.operation_logs;

CREATE TABLE public.operation_logs (
	id serial4 NOT NULL,
	operation_type varchar(100) NOT NULL,
	entity_type varchar(100) NULL,
	entity_id int4 NULL,
	details jsonb NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT operation_logs_pkey PRIMARY KEY (id)
);


-- public.operator_blacklist definition

-- Drop table

-- DROP TABLE public.operator_blacklist;

CREATE TABLE public.operator_blacklist (
	id serial4 NOT NULL,
	operator_name varchar(100) NOT NULL,
	error_message text NULL,
	first_seen_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	hit_count int4 DEFAULT 1 NULL,
	is_active bool DEFAULT true NULL,
	CONSTRAINT operator_blacklist_operator_name_key UNIQUE (operator_name),
	CONSTRAINT operator_blacklist_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_operator_blacklist_active ON public.operator_blacklist USING btree (is_active);
CREATE INDEX idx_operator_blacklist_name ON public.operator_blacklist USING btree (operator_name);


-- public.operator_prefs definition

-- Drop table

-- DROP TABLE public.operator_prefs;

CREATE TABLE public.operator_prefs (
	operator_name varchar(100) NOT NULL,
	status varchar(50) DEFAULT 'ACTIVE'::character varying NULL,
	usage_count int4 DEFAULT 0 NULL,
	success_count int4 DEFAULT 0 NULL,
	failure_rate float8 DEFAULT 0.0 NULL,
	updated_at timestamptz DEFAULT now() NULL,
	CONSTRAINT operator_prefs_pkey PRIMARY KEY (operator_name)
);


-- public.operators definition

-- Drop table

-- DROP TABLE public.operators;

CREATE TABLE public.operators (
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


-- public.pyramid_multipliers definition

-- Drop table

-- DROP TABLE public.pyramid_multipliers;

CREATE TABLE public.pyramid_multipliers (
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

-- Table Triggers

create trigger update_pyramid_multipliers_updated_at before
update
    on
    public.pyramid_multipliers for each row execute function update_updated_at_column();


-- public.regions definition

-- Drop table

-- DROP TABLE public.regions;

CREATE TABLE public.regions (
	id serial4 NOT NULL,
	code varchar(10) NOT NULL,
	"name" varchar(100) NOT NULL,
	description text NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT regions_code_key UNIQUE (code),
	CONSTRAINT regions_pkey PRIMARY KEY (id)
);


-- public.rl_states definition

-- Drop table

-- DROP TABLE public.rl_states;

CREATE TABLE public.rl_states (
	id serial4 NOT NULL,
	state_key varchar(200) NOT NULL,
	state_type varchar(50) NOT NULL,
	q_value numeric(10, 6) DEFAULT 0.0 NULL,
	visit_count int4 DEFAULT 0 NULL,
	success_count int4 DEFAULT 0 NULL,
	meta_data jsonb NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT rl_states_pkey PRIMARY KEY (id),
	CONSTRAINT rl_states_state_key_key UNIQUE (state_key)
);


-- public.system_configs definition

-- Drop table

-- DROP TABLE public.system_configs;

CREATE TABLE public.system_configs (
	id serial4 NOT NULL,
	config_key varchar(100) NOT NULL,
	config_value text NULL,
	config_type varchar(50) NULL,
	description text NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT system_configs_config_key_key UNIQUE (config_key),
	CONSTRAINT system_configs_pkey PRIMARY KEY (id)
);


-- public.template_evaluations definition

-- Drop table

-- DROP TABLE public.template_evaluations;

CREATE TABLE public.template_evaluations (
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


-- public.template_variables definition

-- Drop table

-- DROP TABLE public.template_variables;

CREATE TABLE public.template_variables (
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


-- public.templates definition

-- Drop table

-- DROP TABLE public.templates;

CREATE TABLE public.templates (
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

-- Table Triggers

create trigger update_templates_updated_at before
update
    on
    public.templates for each row execute function update_updated_at_column();


-- public.wqb_credentials definition

-- Drop table

-- DROP TABLE public.wqb_credentials;

CREATE TABLE public.wqb_credentials (
	id serial4 NOT NULL,
	username_encrypted text NOT NULL,
	password_encrypted text NOT NULL,
	is_active bool DEFAULT true NULL,
	last_used_at timestamp NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT wqb_credentials_pkey PRIMARY KEY (id)
);


-- public.datafields definition

-- Drop table

-- DROP TABLE public.datafields;

CREATE TABLE public.datafields (
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
	category varchar(100) NULL,
	subcategory varchar(100) NULL,
	date_coverage float8 NULL,
	coverage float8 NULL,
	pyramid_multiplier float8 NULL,
	alpha_count int4 NULL,
	CONSTRAINT datafields_dataset_id_field_id_key UNIQUE (dataset_id, field_id),
	CONSTRAINT datafields_pkey PRIMARY KEY (id),
	CONSTRAINT uq_datafield_dataset_field UNIQUE (dataset_id, field_id),
	CONSTRAINT datafields_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id)
);
CREATE INDEX idx_datafields_region_delay_universe ON public.datafields USING btree (region, delay, universe);


-- public.rl_actions definition

-- Drop table

-- DROP TABLE public.rl_actions;

CREATE TABLE public.rl_actions (
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


-- public.template_datasets definition

-- Drop table

-- DROP TABLE public.template_datasets;

CREATE TABLE public.template_datasets (
	id serial4 NOT NULL,
	template_id int4 NULL,
	dataset_id int4 NULL,
	priority int4 DEFAULT 0 NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT template_datasets_pkey PRIMARY KEY (id),
	CONSTRAINT template_datasets_template_id_dataset_id_key UNIQUE (template_id, dataset_id),
	CONSTRAINT template_datasets_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES public.datasets(id)
);


-- public.trace_steps definition

-- Drop table

-- DROP TABLE public.trace_steps;

CREATE TABLE public.trace_steps (
	id serial4 NOT NULL,
	task_id int4 NOT NULL,
	step_type varchar(50) NOT NULL,
	step_order int4 NOT NULL,
	input_data jsonb DEFAULT '{}'::jsonb NULL,
	output_data jsonb DEFAULT '{}'::jsonb NULL,
	duration_ms int4 NULL,
	status varchar(50) DEFAULT 'RUNNING'::character varying NULL,
	error_message text NULL,
	created_at timestamptz DEFAULT now() NULL,
	iteration int4 DEFAULT 1 NULL,
	CONSTRAINT trace_steps_pkey PRIMARY KEY (id),
	CONSTRAINT trace_steps_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.mining_tasks(id) ON DELETE CASCADE
);


-- public.universes definition

-- Drop table

-- DROP TABLE public.universes;

CREATE TABLE public.universes (
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


-- public.alpha_base definition

-- Drop table

-- DROP TABLE public.alpha_base;

CREATE TABLE public.alpha_base (
	id serial4 NOT NULL,
	task_id int4 NULL,
	trace_step_id int4 NULL,
	alpha_id varchar(100) NULL,
	"expression" text NOT NULL,
	hypothesis text NULL,
	logic_explanation text NULL,
	region varchar(50) NULL,
	universe varchar(100) NULL,
	dataset_id varchar(100) NULL,
	fields_used jsonb NULL,
	operators_used jsonb NULL,
	simulation_status varchar(50) NULL,
	quality_status varchar(50) NULL,
	diversity_status varchar(50) NULL,
	human_feedback varchar(50) NULL,
	feedback_comment text NULL,
	metrics jsonb NULL,
	pnl_data jsonb NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT alpha_base_pkey PRIMARY KEY (id),
	CONSTRAINT alpha_base_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.mining_tasks(id),
	CONSTRAINT alpha_base_trace_step_id_fkey FOREIGN KEY (trace_step_id) REFERENCES public.trace_steps(id)
);
CREATE INDEX idx_alpha_quality ON public.alpha_base USING btree (quality_status);
CREATE INDEX idx_alpha_region ON public.alpha_base USING btree (region);
CREATE UNIQUE INDEX ix_alpha_base_alpha_id ON public.alpha_base USING btree (alpha_id);
CREATE INDEX ix_alpha_base_id ON public.alpha_base USING btree (id);


-- public.alpha_failures definition

-- Drop table

-- DROP TABLE public.alpha_failures;

CREATE TABLE public.alpha_failures (
	id serial4 NOT NULL,
	task_id int4 NULL,
	trace_step_id int4 NULL,
	"expression" text NULL,
	error_type varchar(100) NULL,
	error_message text NULL,
	raw_response text NULL,
	is_analyzed bool DEFAULT false NULL,
	created_at timestamptz DEFAULT now() NULL,
	CONSTRAINT alpha_failures_pkey PRIMARY KEY (id),
	CONSTRAINT alpha_failures_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.mining_tasks(id) ON DELETE SET NULL,
	CONSTRAINT alpha_failures_trace_step_id_fkey FOREIGN KEY (trace_step_id) REFERENCES public.trace_steps(id) ON DELETE SET NULL
);


-- public.alphas definition

-- Drop table

-- DROP TABLE public.alphas;

CREATE TABLE public.alphas (
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
	task_id int4 NULL,
	trace_step_id int4 NULL,
	human_feedback varchar(50) DEFAULT 'NONE'::character varying NULL,
	feedback_comment text NULL,
	metrics jsonb DEFAULT '{}'::jsonb NULL,
	fields_used jsonb DEFAULT '[]'::jsonb NULL,
	operators_used jsonb DEFAULT '[]'::jsonb NULL,
	quality_status varchar(50) DEFAULT 'PENDING'::character varying NULL,
	hypothesis text NULL,
	logic_explanation text NULL,
	settings jsonb NULL,
	checks jsonb NULL,
	is_metrics jsonb NULL,
	os_metrics jsonb NULL,
	"type" varchar(20) DEFAULT 'REGULAR'::character varying NULL,
	dataset_id varchar(50) NULL,
	CONSTRAINT alphas_pkey PRIMARY KEY (id),
	CONSTRAINT uq_alpha_id UNIQUE (alpha_id),
	CONSTRAINT alphas_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.mining_tasks(id) ON DELETE SET NULL,
	CONSTRAINT alphas_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.templates(id),
	CONSTRAINT alphas_trace_step_id_fkey FOREIGN KEY (trace_step_id) REFERENCES public.trace_steps(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX idx_alphas_alpha_id_unique ON public.alphas USING btree (alpha_id) WHERE (alpha_id IS NOT NULL);
CREATE INDEX idx_alphas_composite_score ON public.alphas USING btree (composite_score DESC);
CREATE INDEX idx_alphas_is_all_pass ON public.alphas USING btree (is_all_pass) WHERE (is_all_pass = true);
CREATE INDEX idx_alphas_region_delay_universe ON public.alphas USING btree (region, delay, universe);
CREATE INDEX idx_alphas_status ON public.alphas USING btree (status);
CREATE INDEX idx_alphas_template_id ON public.alphas USING btree (template_id);

-- Table Triggers

create trigger update_alphas_updated_at before
update
    on
    public.alphas for each row execute function update_updated_at_column();



-- DROP FUNCTION public.update_updated_at_column();

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;