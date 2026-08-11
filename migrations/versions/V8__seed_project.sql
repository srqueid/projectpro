-- V8__seed_project.sql

INSERT INTO project (organization_id, name, description) VALUES
((SELECT id FROM organization WHERE name = 'Empresa A'), 'Projeto Alpha', 'Descrição do Projeto Alpha'),
((SELECT id FROM organization WHERE name = 'Empresa A'), 'Projeto Beta', 'Descrição do Projeto Beta'),
((SELECT id FROM organization WHERE name = 'Empresa B'), 'Projeto Gamma', 'Descrição do Projeto Gamma');
