-- V18__seed_workflow.sql

INSERT INTO workflow (project_id, name, description) VALUES
(
    (SELECT id FROM project WHERE name = 'Projeto Alpha'),
    'Workflow Padrão',
    'Workflow padrão para o Projeto Alpha'
);
