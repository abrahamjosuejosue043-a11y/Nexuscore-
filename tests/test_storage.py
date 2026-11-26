import os
import tempfile
import unittest
from pathlib import Path

from main import build_conversation_title, build_prompt, enforce_chat_rate_limit, select_shared_memories


class StorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = str(Path(cls.temp_dir.name) / "test.db")
        from backend import storage
        cls.storage = storage
        cls.storage.initialize()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_save_and_read_conversation(self):
        self.storage.save_message("user", "geral", "Teste de persistência")
        items = self.storage.messages(10)
        self.assertTrue(any(item["content"] == "Teste de persistência" for item in items))

    def test_save_and_download_artifact(self):
        artifact_id = self.storage.save_artifact("Relatório", "relatorio.txt", "txt", "text/plain", b"conteudo")
        item = self.storage.artifact(artifact_id)
        self.assertEqual(item["content"], b"conteudo")
        self.assertEqual(item["filename"], "relatorio.txt")

    def test_list_artifacts_hides_binary_content(self):
        self.storage.save_artifact("Arquivo", "arquivo.md", "md", "text/markdown", b"# teste")
        items = self.storage.artifacts(10)
        self.assertTrue(any(item["filename"] == "arquivo.md" for item in items))
        self.assertNotIn("content", items[0])

    def test_save_and_read_idea(self):
        idea_id = self.storage.save_idea("Ideia de teste", "Resumo de teste", "alta")
        items = self.storage.ideas(10)
        self.assertTrue(any(item["id"] == idea_id for item in items))

    def test_database_health_reports_wal_and_existing_file(self):
        health = self.storage.health()
        self.assertEqual(health["engine"], "sqlite")
        self.assertTrue(health["database_exists"])
        self.assertEqual(health["journal_mode"], "wal")
        self.assertGreaterEqual(health["table_count"], 5)

    def test_postgres_insert_returns_created_id(self):
        class FakeCursor:
            rowcount = 1

            def fetchone(self):
                return {"id": 123}

        class FakeConnection:
            def __init__(self):
                self.statement = None
                self.params = None

            def execute(self, statement, params):
                self.statement = statement
                self.params = params
                return FakeCursor()

        raw = FakeConnection()
        db = self.storage._PostgresConnection(raw)
        cursor = db.execute(
            "INSERT INTO ideas(title, summary, priority) VALUES(?,?,?)",
            ("Ideia", "Resumo", "media"),
        )
        self.assertIn("RETURNING id", raw.statement)
        self.assertEqual(cursor.lastrowid, 123)
        self.assertEqual(raw.params, ("Ideia", "Resumo", "media"))

    def test_conversation_context_returns_latest_messages_in_order(self):
        conversation_id = "thread-latest-context"
        self.storage.ensure_conversation(conversation_id, "Contexto recente", "geral")
        for index in range(12):
            self.storage.save_message(
                "user" if index % 2 == 0 else "assistant",
                "geral",
                f"Mensagem {index}",
                conversation_id=conversation_id,
            )

        items = self.storage.conversation_messages(conversation_id, limit=8)
        self.assertEqual(
            [item["content"] for item in items],
            [f"Mensagem {index}" for index in range(4, 12)],
        )

    def test_chat_conversation_groups_messages_and_can_be_renamed(self):
        conversation_id = "thread-test-001"
        created = self.storage.ensure_conversation(
            conversation_id, "Organizar projetos", "geral"
        )
        self.assertEqual(created["title"], "Organizar projetos")

        # A retomada da mesma conversa não pode substituir o título original.
        same = self.storage.ensure_conversation(
            conversation_id, "Outro assunto", "geral"
        )
        self.assertEqual(same["title"], "Organizar projetos")

        self.storage.save_message(
            "user", "geral", "Quero organizar meus projetos", conversation_id=conversation_id
        )
        self.storage.save_message(
            "assistant", "geral", "Vamos criar uma estrutura.", "Groq",
            conversation_id=conversation_id,
        )

        messages = self.storage.conversation_messages(conversation_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

        listed = self.storage.list_conversations(100)
        item = next(x for x in listed if x["id"] == conversation_id)
        self.assertEqual(item["message_count"], 2)
        self.assertTrue(self.storage.rename_conversation(conversation_id, "Projetos organizados"))
        self.assertEqual(
            self.storage.get_conversation(conversation_id)["title"],
            "Projetos organizados",
        )

    def test_legacy_messages_are_grouped_in_previous_history(self):
        self.storage.save_message("user", "geral", "Mensagem antiga sem sessão")
        with self.storage.connection() as db:
            self.storage._backfill_legacy_messages(db)
        legacy = self.storage.get_conversation("legacy")
        self.assertEqual(legacy["title"], "Histórico anterior")
        self.assertTrue(
            any(
                x["content"] == "Mensagem antiga sem sessão"
                for x in self.storage.conversation_messages("legacy")
            )
        )

    def test_shared_memory_is_visible_globally_and_by_department(self):
        global_id = self.storage.save_shared_memory(
            "Objetivo central",
            "O Nexuscore deve registrar decisões importantes e relatórios.",
            "objetivo",
            "todos",
        )
        engineering_id = self.storage.save_shared_memory(
            "Padrão de engenharia",
            "Toda alteração precisa de testes automatizados.",
            "processo",
            "programacao",
        )

        engineering = self.storage.shared_memories(100, department="programacao")
        marketing = self.storage.shared_memories(100, department="publicidade")
        engineering_ids = {item["id"] for item in engineering}
        marketing_ids = {item["id"] for item in marketing}

        self.assertIn(global_id, engineering_ids)
        self.assertIn(global_id, marketing_ids)
        self.assertIn(engineering_id, engineering_ids)
        self.assertNotIn(engineering_id, marketing_ids)

    def test_conversation_can_be_linked_to_an_existing_project(self):
        project_id = self.storage.save_project(
            "Projeto vinculado", "Projeto usado para testar o contexto da conversa."
        )
        conversation_id = "conversation-project-link"
        session = self.storage.ensure_conversation(
            conversation_id, "Conversa vinculada", "geral"
        )
        self.assertIsNone(session["project_id"])
        self.assertTrue(
            self.storage.set_conversation_project(conversation_id, project_id)
        )
        linked = self.storage.get_conversation(conversation_id)
        self.assertEqual(linked["project_id"], project_id)
        listed = next(
            item for item in self.storage.list_conversations(200)
            if item["id"] == conversation_id
        )
        self.assertEqual(listed["project_id"], project_id)
        self.assertFalse(
            self.storage.set_conversation_project(conversation_id, 999999)
        )
        self.assertEqual(
            self.storage.get_conversation(conversation_id)["project_id"], project_id
        )
        self.assertTrue(self.storage.set_conversation_project(conversation_id, None))
        self.assertIsNone(
            self.storage.get_conversation(conversation_id)["project_id"]
        )

    def test_department_tasks_are_assigned_and_track_progress(self):
        task_id = self.storage.create_department_task(
            "Validar fluxo de login",
            "Revisar autenticação e escrever testes automatizados.",
            "programacao",
            "alta",
            created_by="geral",
        )
        engineering = self.storage.list_department_tasks(
            100, department="programacao"
        )
        marketing = self.storage.list_department_tasks(
            100, department="publicidade"
        )
        task = next(item for item in engineering if item["id"] == task_id)
        self.assertEqual(task["status"], "pendente")
        self.assertEqual(task["priority"], "alta")
        self.assertFalse(any(item["id"] == task_id for item in marketing))

        self.assertTrue(
            self.storage.update_department_task(
                task_id, "em_andamento", "Auditoria iniciada."
            )
        )
        updated = next(
            item for item in self.storage.list_department_tasks(100, "programacao")
            if item["id"] == task_id
        )
        self.assertEqual(updated["status"], "em_andamento")
        self.assertEqual(updated["result"], "Auditoria iniciada.")

        self.assertTrue(
            self.storage.update_department_task(
                task_id, "concluida", "Testes revisados e aprovados."
            )
        )
        completed = next(
            item for item in self.storage.list_department_tasks(100, "programacao")
            if item["id"] == task_id
        )
        self.assertEqual(completed["status"], "concluida")
        self.assertIsNotNone(completed["completed_at"])
        self.assertEqual(completed["result"], "Testes revisados e aprovados.")

    def test_department_tasks_can_be_isolated_by_conversation_and_project(self):
        conversation_a = self.storage.create_department_task(
            "Tarefa conversa A", "Contexto exclusivo da conversa A.",
            "programacao", "alta", conversation_id="conversation-a", project_id=11,
        )
        conversation_b = self.storage.create_department_task(
            "Tarefa conversa B", "Contexto exclusivo da conversa B.",
            "programacao", "media", conversation_id="conversation-b", project_id=22,
        )
        unlinked = self.storage.create_department_task(
            "Tarefa sem vínculo", "Não deve entrar em contexto de conversa.",
            "programacao", "baixa",
        )

        tasks_a = self.storage.list_department_tasks(
            100, department="programacao", conversation_id="conversation-a"
        )
        self.assertEqual([item["id"] for item in tasks_a], [conversation_a])
        self.assertNotIn(conversation_b, {item["id"] for item in tasks_a})
        self.assertNotIn(unlinked, {item["id"] for item in tasks_a})

        tasks_project_22 = self.storage.list_department_tasks(
            100, department="programacao", project_id=22
        )
        self.assertEqual([item["id"] for item in tasks_project_22], [conversation_b])

        # Sem filtros, o quadro administrativo continua exibindo todas as tarefas.
        all_tasks = self.storage.list_department_tasks(100, department="programacao")
        self.assertTrue(
            {conversation_a, conversation_b, unlinked}.issubset(
                {item["id"] for item in all_tasks}
            )
        )

    def test_archived_memory_is_no_longer_shared_but_is_preserved(self):
        memory_id = self.storage.save_shared_memory(
            "Decisão temporária", "Este registro será arquivado.", "decisao", "todos"
        )
        self.assertTrue(self.storage.archive_shared_memory(memory_id))
        self.assertFalse(
            any(item["id"] == memory_id for item in self.storage.shared_memories(100))
        )
        archived = self.storage.shared_memories(100, include_archived=True)
        item = next(item for item in archived if item["id"] == memory_id)
        self.assertEqual(item["status"], "archived")

    def test_postgres_placeholder_adapter_preserves_legacy_queries(self):
        self.assertEqual(
            self.storage._qmark_to_pyformat(
                "INSERT INTO email_log(direction, recipient) VALUES(?,?)"
            ),
            "INSERT INTO email_log(direction, recipient) VALUES(%s,%s)",
        )

    def test_connection_rolls_back_failed_transaction(self):
        with self.assertRaises(RuntimeError):
            with self.storage.connection() as db:
                db.execute(
                    "INSERT INTO ideas(title, summary, priority) VALUES(?,?,?)",
                    ("Não salvar", "transação de teste", "media"),
                )
                raise RuntimeError("forçar rollback")
        items = self.storage.ideas(300)
        self.assertFalse(any(item["title"] == "Não salvar" for item in items))


class SharedPromptTests(unittest.TestCase):
    def test_prompt_includes_conversation_history_and_shared_memory(self):
        prompt = build_prompt(
            "Qual é a próxima etapa?",
            "diretoria",
            conversation_history=[
                {"role": "user", "content": "Nosso objetivo é lançar o Nexuscore."},
                {"role": "assistant", "content": "Precisamos definir as prioridades."},
            ],
            shared_memories=[
                {
                    "title": "Objetivo do projeto",
                    "content": "Lançar uma versão estável antes de adicionar novas funções.",
                    "category": "objetivo",
                }
            ],
        )
        self.assertIn("Nosso objetivo é lançar o Nexuscore.", prompt)
        self.assertIn("Lançar uma versão estável", prompt)
        self.assertIn("MEMÓRIA COMPARTILHADA", prompt)
        self.assertIn("CONTEXTO DESTA CONVERSA", prompt)

    def test_prompt_includes_tasks_assigned_to_current_department(self):
        prompt = build_prompt(
            "Vamos trabalhar na tarefa atribuída?",
            "programacao",
            department_tasks=[
                {
                    "id": 21,
                    "title": "Validar fluxo de login",
                    "description": "Revisar autenticação e criar testes.",
                    "status": "pendente",
                    "priority": "alta",
                    "result": "",
                }
            ],
        )
        self.assertIn("FILA DE TAREFAS DO SEU DEPARTAMENTO", prompt)
        self.assertIn("Validar fluxo de login", prompt)
        self.assertIn("Revisar autenticação e criar testes", prompt)
        self.assertIn("não pode alterar", prompt)

    def test_memory_selector_does_not_inject_unrelated_memories(self):
        memories = [
            {
                "title": "Planejamento financeiro",
                "content": "Acompanhar receitas e despesas mensais.",
                "category": "objetivo",
                "updated_at": "2026-11-26",
            }
        ]
        selected = select_shared_memories(
            "Como melhorar a iluminação do escritório?", memories, limit=6
        )
        self.assertEqual(selected, [])

    def test_chat_rate_limit_blocks_requests_over_window_and_recovers(self):
        client_ip = "unit-test-rate-limit-security"
        for _ in range(20):
            enforce_chat_rate_limit(client_ip, now=100.0)

        with self.assertRaises(Exception) as captured:
            enforce_chat_rate_limit(client_ip, now=100.0)
        self.assertEqual(captured.exception.status_code, 429)
        self.assertIn("Retry-After", captured.exception.headers)

        # Depois da janela, a mesma origem pode voltar a usar o chat.
        enforce_chat_rate_limit(client_ip, now=161.0)

    def test_memory_selector_prefers_matching_subject(self):
        memories = [
            {
                "title": "Estratégia financeira",
                "content": "Controlar receitas, despesas e fluxo de caixa.",
                "category": "objetivo",
                "updated_at": "2026-11-25",
            },
            {
                "title": "Calendário de marketing",
                "content": "Planejar campanhas e publicações.",
                "category": "processo",
                "updated_at": "2026-11-26",
            },
        ]
        selected = select_shared_memories("Como acompanhar o fluxo de caixa?", memories, limit=1)
        self.assertEqual(selected[0]["title"], "Estratégia financeira")


class ConversationTitleTests(unittest.TestCase):
    def test_title_is_derived_from_first_message(self):
        title = build_conversation_title(
            "Bom dia! Quero organizar conversas por assunto e agente no Nexuscore"
        )
        self.assertEqual(
            title,
            "Organizar conversas por assunto e agente no Nexuscore",
        )

    def test_empty_conversation_title_has_safe_fallback(self):
        self.assertEqual(build_conversation_title("  "), "Nova conversa")


if __name__ == "__main__":
    unittest.main()
