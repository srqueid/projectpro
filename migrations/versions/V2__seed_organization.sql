-- V2__seed_organization.sql

INSERT INTO organization (name, legal_name, document, email, phone, timezone, locale, status) VALUES
('Empresa A', 'Empresa A Ltda.', '12.345.678/0001-90', 'contato@empresa-a.com', '+55 11 99999-9999', 'America/Sao_Paulo', 'pt-BR', 'active'),
('Empresa B', 'Empresa B S.A.', '98.765.432/0001-10', 'contato@empresa-b.com', '+55 21 88888-8888', 'America/Sao_Paulo', 'pt-BR', 'active')
ON CONFLICT (email) DO NOTHING;
