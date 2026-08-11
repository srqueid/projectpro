-- V16__seed_work_item_relationship.sql

INSERT INTO work_item_relationship (source_work_item_id, target_work_item_id, relationship_type) VALUES
(
    (SELECT id FROM work_item WHERE title = 'Meu primeiro bug'),
    (SELECT id FROM work_item WHERE title = 'Minha primeira tarefa'),
    'blocks'
);
