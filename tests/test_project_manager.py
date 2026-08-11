
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


class TestConversaoTipoAlcada(unittest.TestCase):
    """Testes para a matriz de promoção/rebaixamento com alçada por perfil."""

    def setUp(self):
        """Configura o mock do banco para os testes de conversão."""
        self.patcher = patch('app.database.get_db')
        self.mock_get_db = self.patcher.start()
        self.mock_conn = MagicMock()
        self.mock_get_db.return_value = self.mock_conn
        self.mock_cur = self.mock_conn.cursor.return_value.__enter__.return_value

    def tearDown(self):
        """Finaliza o mock do banco."""
        self.patcher.stop()

    def test_perfil_de_aprovacao_epic_feature(self):
        """Transição Feature ↔ Épico requer Gerente de Produto."""
        self.assertEqual(project_manager._perfil_de_aprovacao('feature', 'epic'), 'product_manager')
        self.assertEqual(project_manager._perfil_de_aprovacao('epic', 'feature'), 'product_manager')

    def test_perfil_de_aprovacao_feature_story_task(self):
        """Transições Tarefa/História ↔ Feature requerem Dono do Produto."""
        self.assertEqual(project_manager._perfil_de_aprovacao('story', 'feature'), 'product_owner')
        self.assertEqual(project_manager._perfil_de_aprovacao('feature', 'story'), 'product_owner')
        self.assertEqual(project_manager._perfil_de_aprovacao('task', 'feature'), 'product_owner')
        self.assertEqual(project_manager._perfil_de_aprovacao('feature', 'task'), 'product_owner')

    def test_perfil_de_aprovacao_operacional_livre(self):
        """Transições operacionais (subtask↔task, story↔task) são livres."""
        self.assertEqual(project_manager._perfil_de_aprovacao('subtask', 'task'), 'executor')
        self.assertEqual(project_manager._perfil_de_aprovacao('task', 'subtask'), 'executor')
        self.assertEqual(project_manager._perfil_de_aprovacao('story', 'task'), 'executor')
        self.assertEqual(project_manager._perfil_de_aprovacao('task', 'story'), 'executor')

    def test_tem_permissao_aprovacao_hierarquia(self):
        """Perfis com nível igual ou superior podem aprovar."""
        # Executor não aprova transição que exige PO nem PM
        self.assertFalse(project_manager._tem_permissao_aprovacao('executor', 'product_owner'))
        self.assertFalse(project_manager._tem_permissao_aprovacao('executor', 'product_manager'))
        # Executor aprova transições que exigem executor
        self.assertTrue(project_manager._tem_permissao_aprovacao('executor', 'executor'))
        # PO aprova o que exige PO e executores, mas não PM
        self.assertTrue(project_manager._tem_permissao_aprovacao('product_owner', 'product_owner'))
        self.assertTrue(project_manager._tem_permissao_aprovacao('product_owner', 'executor'))
        self.assertFalse(project_manager._tem_permissao_aprovacao('product_owner', 'product_manager'))
        # PM aprova tudo
        self.assertTrue(project_manager._tem_permissao_aprovacao('product_manager', 'product_manager'))
        self.assertTrue(project_manager._tem_permissao_aprovacao('product_manager', 'product_owner'))
        self.assertTrue(project_manager._tem_permissao_aprovacao('product_manager', 'executor'))

    def test_converter_um_nivel_promover(self):
        """Promover subir um nível na hierarquia."""
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'subtask'}, 'promover'), 'task')
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'task'}, 'promover'), 'story')
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'story'}, 'promover'), 'feature')
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'feature'}, 'promover'), 'epic')
        # Épico no topo não pode ser promovido
        self.assertIsNone(project_manager._converter_um_nivel({'tipo': 'epic'}, 'promover'))

    def test_converter_um_nivel_rebaixar(self):
        """Rebaixar desce um nível na hierarquia."""
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'epic'}, 'rebaixar'), 'feature')
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'feature'}, 'rebaixar'), 'story')
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'story'}, 'rebaixar'), 'task')
        self.assertEqual(project_manager._converter_um_nivel({'tipo': 'task'}, 'rebaixar'), 'subtask')
        # Subtarefa no fundo não pode ser rebaixada
        self.assertIsNone(project_manager._converter_um_nivel({'tipo': 'subtask'}, 'rebaixar'))

    def test_converter_tipo_bloqueado_por_alcada(self):
        """
        Um Executor tentando promover uma Feature para Épico deve ser
        barrado pela regra de alçada (exige Gerente de Produto).
        """
        # Mock do cursor para simular a tarefa e o responsável
        self.mock_cur.fetchone.side_effect = [
            {'id': 1, 'tipo': 'feature', 'tarefa': 'F', 'subtarefa': None, 'parent_id': None, 'pk_id': 42},
            {'perfil': 'executor'}
        ]
        with self.assertRaises(PermissionError):
            project_manager.converter_tipo_tarefa('PROJ', 1, 'promover', responsavel_id='u1')

    def test_converter_tipo_promover_subtask_para_task(self):
        """
        Um Executor pode promover uma Subtarefa para Tarefa (transição livre).
        Deve retornar sucesso com os tipos corretos.
        """
        # Tarefa encontrada + perfil do responsável (executor) + pai não existe
        self.mock_cur.fetchone.side_effect = [
            {'id': 5, 'tipo': 'subtask', 'tarefa': 'S', 'subtarefa': None, 'parent_id': None, 'pk_id': 99},
            {'perfil': 'executor'}
        ]
        # Como não há pai nem filhos, os SELECTs de filhos retornam lista vazia
        self.mock_cur.fetchall.return_value = []

        resultado = project_manager.converter_tipo_tarefa('PROJ', 5, 'promover', responsavel_id='u1')

        self.assertEqual(resultado['status'], 'sucesso')
        self.assertEqual(resultado['tipo_anterior'], 'subtask')
        self.assertEqual(resultado['tipo_novo'], 'task')
        # Garante que o UPDATE do tipo foi executado
        calls = [c[0][0] for c in self.mock_cur.execute.call_args_list]
        self.assertTrue(any('SET tipo' in c for c in calls))


if __name__ == '__main__':
    unittest.main()
