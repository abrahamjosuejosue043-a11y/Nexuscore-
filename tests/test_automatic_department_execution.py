"""Tests for the automatic department executor and audit trail."""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from backend import storage
import main


class AutomaticDepartmentExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = storage.DB_PATH
        self.old_database_url = os.environ.pop("DATABASE_URL", None)
        storage.DB_PATH = os.path.join(self.temp_dir.name, "automatic-execution.db")
        storage.initialize()
        self.project_id = storage.save_project(
            "Projeto de execução automática",
            "Projeto isolado para testes do executor.",
        )
        storage.decide_project(self.project_id, "aprovado", actor="ceo")

    def tearDown(self):
        storage.DB_PATH = self.old_path
        if self.old_database_url is not None:
            os.environ["DATABASE_URL"] = self.old_database_url
        else:
            os.environ.pop("DATABASE_URL", None)
        self.temp_dir.cleanup()

    def _create_auto_task(self, department="publicidade", title="Criar estratégia de campanha",
                          description=None):
        description = description or (
            "Produzir uma estratégia textual com público-alvo, objetivos, canais, "
            "calendário de conteúdo e métricas de sucesso. Critérios de aceitação: "
            "incluir os cinco itens e uma recomendação final."
        )
        plan_id = storage.create_work_plan(
            "Plano de execução", "Executar uma entrega textual.", "Plano de teste.",
            self.project_id,
            [{
                "title": title,
                "description": description,
                "department": department,
                "priority": "media",
            }],
            conversation_id="auto-execution-test",
        )
        task_ids = storage.approve_work_plan(plan_id, auto_dispatch=True)
        self.assertEqual(len(task_ids), 1)
        return task_ids[0]

    def _task(self, task_id):
        tasks = storage.list_department_tasks(limit=100, project_id=self.project_id)
        return next(task for task in tasks if int(task["id"]) == int(task_id))

    def test_claim_only_returns_tasks_marked_for_automatic_dispatch(self):
        manual_plan = storage.create_work_plan(
            "Plano manual", "Objetivo manual.", "Resumo manual.", self.project_id,
            [{
                "title": "Tarefa manual",
                "description": "Não deve ser processada automaticamente.",
                "department": "publicidade",
                "priority": "media",
            }],
        )
        storage.approve_work_plan(manual_plan)
        automatic_id = self._create_auto_task()

        claimed = storage.claim_next_automated_task()
        self.assertEqual(claimed["id"], automatic_id)
        self.assertEqual(claimed["status"], "em_andamento")
        self.assertEqual(self._task(automatic_id)["status"], "em_andamento")
        self.assertIsNone(storage.claim_next_automated_task())

    def test_automatic_executor_generates_reviews_and_completes_textual_delivery(self):
        task_id = self._create_auto_task()
        claimed = storage.claim_next_automated_task()
        model = AsyncMock(side_effect=[
            (
                "Estratégia entregue: público-alvo definido, objetivos, canais, calendário "
                "editorial e métricas de acompanhamento, com recomendação final.",
                "test-model",
            ),
            (json.dumps({"approved": True, "feedback": "Todos os critérios textuais foram atendidos."}), "review-model"),
        ])
        with patch("main.chamar_groq", new=model):
            result = asyncio.run(main.execute_claimed_automated_task(claimed))

        self.assertEqual(result["status"], "concluida")
        self.assertEqual(model.await_count, 2)
        task = self._task(task_id)
        self.assertEqual(task["status"], "concluida")
        self.assertIn("Estratégia entregue", task["result"])
        inputs = storage.project_progress_inputs(self.project_id)
        completed = next(item for item in inputs["tasks"] if int(item["id"]) == task_id)
        self.assertEqual(completed["directorate_validated"], 1)

    def test_programming_task_is_blocked_until_repository_integration_exists(self):
        task_id = self._create_auto_task(
            department="programacao",
            title="Implementar melhoria no repositório",
            description="Alterar código e executar testes automatizados no repositório.",
        )
        claimed = storage.claim_next_automated_task()
        model = AsyncMock()
        with patch("main.chamar_groq", new=model):
            result = asyncio.run(main.execute_claimed_automated_task(claimed))

        self.assertEqual(result["status"], "bloqueada")
        model.assert_not_awaited()
        task = self._task(task_id)
        self.assertEqual(task["status"], "bloqueada")
        self.assertIn("GitHub", task["result"])

    def test_external_action_is_blocked_without_calling_provider(self):
        task_id = self._create_auto_task(
            title="Enviar e-mail da campanha",
            description="Enviar a campanha por e-mail aos clientes e confirmar o envio.",
        )
        claimed = storage.claim_next_automated_task()
        model = AsyncMock()
        with patch("main.chamar_groq", new=model):
            result = asyncio.run(main.execute_claimed_automated_task(claimed))

        self.assertEqual(result["status"], "bloqueada")
        model.assert_not_awaited()
        self.assertIn("nenhuma ação externa", self._task(task_id)["result"].lower())

    def test_failed_director_review_gets_one_correction_then_blocks(self):
        task_id = self._create_auto_task()
        claimed = storage.claim_next_automated_task()
        rejected = json.dumps({"approved": False, "feedback": "Faltam métricas mensuráveis."})
        model = AsyncMock(side_effect=[
            ("Rascunho inicial da estratégia.", "draft-model"),
            (rejected, "review-model"),
            ("Versão corrigida, agora incluindo metas e métricas mensuráveis.", "revision-model"),
            (rejected, "review-model"),
        ])
        with patch("main.chamar_groq", new=model):
            result = asyncio.run(main.execute_claimed_automated_task(claimed))

        self.assertEqual(result["status"], "bloqueada")
        self.assertEqual(model.await_count, 4)
        task = self._task(task_id)
        self.assertEqual(task["status"], "bloqueada")
        self.assertIn("Faltam métricas", task["result"])

    def test_interrupted_automatic_task_is_requeued_with_audit(self):
        task_id = self._create_auto_task()
        storage.claim_next_automated_task()
        storage.update_department_task(
            task_id, "em_revisao", "Entrega parcial para teste de reinicialização.",
            actor="publicidade",
        )
        requeued = storage.requeue_interrupted_automated_tasks()

        self.assertEqual(requeued, [task_id])
        self.assertEqual(self._task(task_id)["status"], "pendente")
        events = storage.list_task_events(task_id)
        self.assertTrue(any(event["event_type"] == "execution_requeued" for event in events))

    def test_daily_budget_stops_claiming_and_reports_remaining_capacity(self):
        first_id = self._create_auto_task(title="Primeira tarefa do limite")
        self._create_auto_task(title="Segunda tarefa do limite")

        claimed = storage.claim_next_automated_task(daily_limit=1)
        self.assertEqual(claimed["id"], first_id)
        self.assertIsNone(storage.claim_next_automated_task(daily_limit=1))

        summary = storage.automated_execution_summary(daily_limit=1)
        self.assertEqual(summary["started_today"], 1)
        self.assertEqual(summary["daily_limit"], 1)
        self.assertEqual(summary["remaining_today"], 0)
        self.assertEqual(summary["counts"]["pendente"], 1)

    def test_summary_counts_only_automatically_dispatched_tasks(self):
        self._create_auto_task()
        summary = storage.automated_execution_summary()
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["counts"]["pendente"], 1)
        self.assertEqual(summary["counts"]["concluida"], 0)
        self.assertEqual(summary["started_today"], 0)
        self.assertEqual(summary["daily_limit"], 10)
        self.assertEqual(summary["remaining_today"], 10)


if __name__ == "__main__":
    unittest.main()
