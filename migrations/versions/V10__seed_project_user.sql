-- V10__seed_project_user.sql

INSERT INTO project_user (project_id, user_id) VALUES
((SELECT id FROM project WHERE name = 'Projeto Alpha'), (SELECT id FROM "user" WHERE email = 'denis.costa@example.com')),
((SELECT id FROM project WHERE name = 'Projeto Alpha'), (SELECT id FROM "user" WHERE email = 'outro.usuario@example.com')),
((SELECT id FROM project WHERE name = 'Projeto Beta'), (SELECT id FROM "user" WHERE email = 'denis.costa@example.com')),
((SELECT id FROM project WHERE name = 'Projeto Gamma'), (SELECT id FROM "user" WHERE email = 'outro.usuario@example.com'));
