-- V4__seed_user.sql

INSERT INTO "user" (name, email, password_hash, status) VALUES
('Denis Costa', 'denis.costa@example.com', 'dummy_hash', 'active'),
('Outro Usuario', 'outro.usuario@example.com', 'dummy_hash', 'active')
ON CONFLICT (email) DO NOTHING;
