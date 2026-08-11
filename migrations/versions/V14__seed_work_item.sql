-- V14__seed_work_item.sql

INSERT INTO work_item (project_id, work_item_type_id, title, description, assignee_id, reporter_id) VALUES
(
    (SELECT id FROM project WHERE name = 'Projeto Alpha'),
    (SELECT id FROM work_item_type WHERE name = 'Task' AND organization_id = (SELECT id FROM organization WHERE name = 'Empresa A')),
    'Minha primeira tarefa',
    'Descrição da minha primeira tarefa',
    (SELECT id FROM "user" WHERE email = 'denis.costa@example.com'),
    (SELECT id FROM "user" WHERE email = 'outro.usuario@example.com')
),
(
    (SELECT id FROM project WHERE name = 'Projeto Alpha'),
    (SELECT id FROM work_item_type WHERE name = 'Bug' AND organization_id = (SELECT id FROM organization WHERE name = 'Empresa A')),
    'Meu primeiro bug',
    'Descrição do meu primeiro bug',
    (SELECT id FROM "user" WHERE email = 'outro.usuario@example.com'),
    (SELECT id FROM "user" WHERE email = 'denis.costa@example.com')
);
