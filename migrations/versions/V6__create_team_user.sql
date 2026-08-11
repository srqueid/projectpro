-- V6__create_team_user.sql

CREATE TABLE IF NOT EXISTS team_user (
    team_id UUID NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    PRIMARY KEY (team_id, user_id)
);

COMMENT ON TABLE team_user IS 'Represents the many-to-many relationship between teams and users.';
