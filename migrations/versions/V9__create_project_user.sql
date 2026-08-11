-- V9__create_project_user.sql

CREATE TABLE IF NOT EXISTS project_user (
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, user_id)
);

COMMENT ON TABLE project_user IS 'Represents the many-to-many relationship between projects and users.';
