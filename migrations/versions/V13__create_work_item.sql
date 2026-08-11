-- V13__create_work_item.sql

CREATE TABLE IF NOT EXISTS work_item (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    work_item_type_id UUID NOT NULL REFERENCES work_item_type(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    reporter_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    due_date DATE,
    start_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE work_item IS 'Represents a work item in a project.';
