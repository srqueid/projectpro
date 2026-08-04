
import unittest
import psycopg2
import psycopg2.extras
from unittest.mock import patch, MagicMock

# Assuming the project structure allows this import
from app import project_manager, config, database

class TestProjectManager(unittest.TestCase):

    def setUp(self):
        """Set up a test database and a clean schema for each test."""
        # Use a separate in-memory SQLite database for testing, or a test PostgreSQL DB
        # For simplicity, we'll patch the database connection
        self.patcher = patch('app.database.get_db')
        self.mock_get_db = self.patcher.start()

        # In-memory SQLite would be ideal for speed, but the app uses psycopg2.
        # So, we'll use a test PostgreSQL database.
        # This requires a test database to be configured.
        # For this example, we'll mock the DB connection entirely.
        self.mock_conn = MagicMock()
        self.mock_get_db.return_value = self.mock_conn
        self.mock_cur = self.mock_conn.cursor.return_value.__enter__.return_value

    def tearDown(self):
        """Clean up after each test."""
        self.patcher.stop()

    def test_carregar_kanban_config_with_existing_config(self):
        """
        Test loading an existing Kanban configuration for a project.
        """
        # Arrange
        project_id = "TEST_PROJECT"
        expected_colunas = [
            {'coluna_id': 'backlog', 'nome': 'Backlog', 'tipo': 'inicio', 'progresso_padrao': 0},
            {'coluna_id': 'done', 'nome': 'Done', 'tipo': 'fim', 'progresso_padrao': 100},
        ]
        
        # Mock the database cursor's fetchall to return the test data
        self.mock_cur.fetchall.return_value = expected_colunas

        # Act
        kanban_config = project_manager.carregar_kanban_config(project_id)

        # Assert
        self.assertIn('colunas', kanban_config)
        self.assertEqual(len(kanban_config['colunas']), 2)
        self.assertEqual(kanban_config['colunas'][0]['nome'], 'Backlog')
        self.assertEqual(kanban_config['colunas'][1]['progresso_padrao'], 100)
        
        # Verify the correct SQL was executed
        self.mock_cur.execute.assert_called_with(
            "SELECT coluna_id, nome, tipo, progresso_padrao, allow_back FROM projeto.kanban_colunas WHERE projeto_id = %s ORDER BY ordem",
            (project_id,)
        )

    def test_carregar_kanban_config_with_no_config(self):
        """
        Test that a default Kanban configuration is created and returned
        when no configuration exists for a project.
        """
        # Arrange
        project_id = "NEW_PROJECT"
        
        # Mock the database cursor's fetchall to return an empty list
        self.mock_cur.fetchall.return_value = []
        
        # We need to also mock the `salvar_kanban_config` function that is called inside
        with patch('app.project_manager.salvar_kanban_config') as mock_salvar:
            # Act
            kanban_config = project_manager.carregar_kanban_config(project_id)

            # Assert
            self.assertIn('colunas', kanban_config)
            self.assertTrue(len(kanban_config['colunas']) > 0)
            self.assertEqual(kanban_config['colunas'][0]['coluna_id'], 'backlog')
            
            # Verify that the default config was saved
            mock_salvar.assert_called_once()
            args, _ = mock_salvar.call_args
            self.assertEqual(args[0], project_id)
            self.assertIn('colunas', args[1])


    def test_salvar_kanban_config(self):
        """
        Test saving a Kanban configuration for a project.
        """
        # Arrange
        project_id = "TEST_PROJECT"
        config_data = {
            'colunas': [
                {'coluna_id': 'todo', 'nome': 'To Do', 'tipo': 'inicio', 'progresso_padrao': 0},
                {'coluna_id': 'doing', 'nome': 'In Progress', 'tipo': 'meio', 'progresso_padrao': 50},
            ]
        }

        # Act
        project_manager.salvar_kanban_config(project_id, config_data)

        # Assert
        self.assertEqual(self.mock_cur.execute.call_count, 3)

        # Check the DELETE call
        self.mock_cur.execute.assert_any_call(
            "DELETE FROM projeto.kanban_colunas WHERE projeto_id = %s",
            (project_id,)
        )

        # Check the INSERT calls
        self.mock_cur.execute.assert_any_call(
            "INSERT INTO projeto.kanban_colunas (projeto_id, coluna_id, nome, tipo, ordem, progresso_padrao, allow_back) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (project_id, 'todo', 'To Do', 'inicio', 0, 0, True)
        )
        self.mock_cur.execute.assert_any_call(
            "INSERT INTO projeto.kanban_colunas (projeto_id, coluna_id, nome, tipo, ordem, progresso_padrao, allow_back) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (project_id, 'doing', 'In Progress', 'meio', 1, 50, True)
        )
        self.mock_conn.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
