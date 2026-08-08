from plugin import MediaHubSmartRenamerPlugin
import pytest


def test_execution_requires_plan_and_confirmation(tmp_path):
    plugin = MediaHubSmartRenamerPlugin(plugin_path=tmp_path)

    with pytest.raises(PermissionError):
        plugin.execute_rename([])

    with pytest.raises(PermissionError):
        plugin.execute_rename()
