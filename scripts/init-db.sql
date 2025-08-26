-- AI Agent Framework Database Initialization Script

-- Create database if it doesn't exist (this is handled by POSTGRES_DB env var)
-- CREATE DATABASE IF NOT EXISTS ai_agent_framework;

-- Create tables for storing agent execution logs
CREATE TABLE IF NOT EXISTS agent_executions (
    id SERIAL PRIMARY KEY,
    correlation_id VARCHAR(255) UNIQUE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    trigger_source VARCHAR(100) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    execution_time FLOAT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_agent_executions_correlation_id ON agent_executions(correlation_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_agent_name ON agent_executions(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_executions_created_at ON agent_executions(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_executions_success ON agent_executions(success);

-- Create table for storing metrics
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    component VARCHAR(255) NOT NULL,
    operation VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    labels JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for metrics
CREATE INDEX IF NOT EXISTS idx_metrics_component ON metrics(component);
CREATE INDEX IF NOT EXISTS idx_metrics_operation ON metrics(operation);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);

-- Create table for storing error logs
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    correlation_id VARCHAR(255),
    component VARCHAR(255) NOT NULL,
    operation VARCHAR(255) NOT NULL,
    error_type VARCHAR(255) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for error logs
CREATE INDEX IF NOT EXISTS idx_error_logs_correlation_id ON error_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_component ON error_logs(component);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for agent_executions table
CREATE TRIGGER update_agent_executions_updated_at 
    BEFORE UPDATE ON agent_executions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_agent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_agent;