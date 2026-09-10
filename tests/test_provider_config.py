"""Tests for the provider boundary configuration contract."""

from __future__ import annotations

import unittest
import json
from pathlib import Path
import tempfile

from pydantic import ValidationError

from thesis_data.experiment_contract import ExperimentArm, ExperimentRunConfig
from thesis_data.provider_config import (
    ProviderBoundaryError,
    ProviderExecutionConfig,
    load_provider_config,
    validate_provider_config_for_run,
)


class ProviderConfigTests(unittest.TestCase):
    def run_config(self) -> ExperimentRunConfig:
        return ExperimentRunConfig(
            run_id="run-1",
            snapshot_id="gold-v1",
            question_set_id="questions-v1",
            question_id="q-1",
            rubric_version="rubric-v1",
            prompt_version="prompt-contract-v1",
            arm=ExperimentArm.SINGLE_AGENT,
            model_id="provider-model-v1",
            source_policy_id="primary-only-v1",
        )

    def test_provider_config_is_compatible_with_run_without_containing_secret(self):
        config = ProviderExecutionConfig(
            adapter_id="openai-responses-v1",
            provider_id="openai",
            model_id="provider-model-v1",
            source_policy_id="primary-only-v1",
            environment="provider_backed",
            network_access="enabled",
            api_key_env_var="THESIS_PROVIDER_API_KEY",
        )

        validate_provider_config_for_run(config, self.run_config())
        self.assertNotIn("api_key", config.model_dump())
        self.assertNotIn("THESIS_PROVIDER_API_KEY_VALUE", config.model_dump_json())

    def test_provider_backed_config_requires_explicit_secret_reference(self):
        with self.assertRaises(ValidationError) as raised:
            ProviderExecutionConfig(
                adapter_id="openai-responses-v1",
                provider_id="openai",
                model_id="provider-model-v1",
                source_policy_id="primary-only-v1",
                environment="provider_backed",
            )

        self.assertIn("api_key_env_var_required", str(raised.exception))

    def test_offline_config_cannot_enable_network(self):
        with self.assertRaises(ValidationError) as raised:
            ProviderExecutionConfig(
                adapter_id="fixture-v1",
                provider_id="offline",
                model_id="offline-fixture-model",
                source_policy_id="offline-fixture-primary-only-v1",
                environment="offline_fixture",
                network_access="enabled",
            )

        self.assertIn("offline_network_forbidden", str(raised.exception))

    def test_run_and_provider_model_or_policy_mismatch_is_rejected(self):
        config = ProviderExecutionConfig(
            adapter_id="openai-responses-v1",
            provider_id="openai",
            model_id="other-model",
            source_policy_id="primary-only-v2",
            environment="provider_backed",
            network_access="enabled",
            api_key_env_var="THESIS_PROVIDER_API_KEY",
        )

        with self.assertRaises(ProviderBoundaryError) as raised:
            validate_provider_config_for_run(config, self.run_config())

        self.assertEqual(
            raised.exception.blockers,
            ("model_id_mismatch", "source_policy_id_mismatch"),
        )

    def test_loader_reads_config_without_opening_a_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "provider-config.json"
            path.write_text(
                json.dumps({
                    "adapter_id": "openai-responses-v1",
                    "provider_id": "openai",
                    "model_id": "provider-model-v1",
                    "source_policy_id": "primary-only-v1",
                    "environment": "provider_backed",
                    "network_access": "enabled",
                    "api_key_env_var": "THESIS_PROVIDER_API_KEY",
                }),
                encoding="utf-8",
            )

            loaded = load_provider_config(path)

        self.assertEqual(loaded.adapter_id, "openai-responses-v1")
        self.assertEqual(loaded.api_key_env_var, "THESIS_PROVIDER_API_KEY")

    def test_loader_rejects_unreadable_or_invalid_config(self):
        with self.assertRaises(ProviderBoundaryError) as raised:
            load_provider_config(Path("does-not-exist/provider-config.json"))

        self.assertEqual(raised.exception.blockers, ("provider_config_unreadable",))


if __name__ == "__main__":
    unittest.main()
