-- V1__create_organization.sql

CREATE TABLE IF NOT EXISTS organization (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    document VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(255),
    timezone VARCHAR(255),
    locale VARCHAR(255),
    status VARCHAR(255) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE organization IS 'Represents an organization, which is the top-level entity in the platform.';
