-- V12__seed_work_item_type.sql

INSERT INTO work_item_type (organization_id, name, description, icon, color) VALUES
((SELECT id FROM organization WHERE name = 'Empresa A'), 'Task', 'A single task', 'task-icon', '#FFFFFF'),
((SELECT id FROM organization WHERE name = 'Empresa A'), 'Bug', 'A bug', 'bug-icon', '#FF0000'),
((SELECT id FROM organization WHERE name = 'Empresa B'), 'Story', 'A user story', 'story-icon', '#00FF00');
