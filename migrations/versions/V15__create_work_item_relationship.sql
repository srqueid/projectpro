-- V15__create_work_item_relationship.sql

CREATE TABLE IF NOT EXISTS work_item_relationship (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_work_item_id UUID NOT NULL REFERENCES work_item(id) ON DELETE CASCADE,
    target_work_item_id UUID NOT NULL REFERENCES work_item(id) ON DELETE CASCADE,
    relationship_type VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE work_item_relationship IS 'Represents a relationship between two work items.';
