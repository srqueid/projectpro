-- V1_1__add_unique_constraint_to_organization.sql

ALTER TABLE organization ADD CONSTRAINT organization_email_key UNIQUE (email);
