from plugin import MediaHubSmartRenamerPlugin
import pytest
def test_execution_remains_locked(tmp_path):
 p=MediaHubSmartRenamerPlugin(plugin_path=tmp_path)
 with pytest.raises(RuntimeError): p.execute_rename([])
