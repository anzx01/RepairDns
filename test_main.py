import unittest
from unittest.mock import Mock, patch

import main


class AppTests(unittest.TestCase):
    def setUp(self):
        self.is_admin = patch('main.core.is_admin', return_value=True)
        self.get_settings = patch('main.core.get_settings', return_value={
            'auto_monitor': False,
            'monitor_interval': 5,
            'auto_repair': False,
            'flush_on_repair': True,
        })
        self.is_admin.start()
        self.get_settings.start()
        self.addCleanup(self.is_admin.stop)
        self.addCleanup(self.get_settings.stop)

    def _create_app(self):
        app = main.App()
        app.withdraw()
        self.addCleanup(lambda: app.winfo_exists() and app._close_app())
        return app

    def test_update_status_without_network_shows_informational_note(self):
        app = self._create_app()

        app.adapters = []
        app.dns_configs = {}
        static_adapters = app._update_status()

        self.assertEqual(static_adapters, [])
        self.assertEqual(app.lbl_status.cget('text'), '未检测到网络')
        self.assertEqual(app.repair_btn.cget('text'), '⚡  无可修复项')
        self.assertEqual(app.note_lbl.cget('text'), '[INFO] 当前未检测到可用网络适配器')

    def test_monitor_refresh_triggers_auto_repair_for_static_dns(self):
        self.get_settings.stop()
        self.get_settings = patch('main.core.get_settings', return_value={
            'auto_monitor': True,
            'monitor_interval': 5,
            'auto_repair': True,
            'flush_on_repair': True,
        })
        self.get_settings.start()
        self.addCleanup(self.get_settings.stop)

        app = self._create_app()
        app._start_repair = Mock()

        adapters = [{'name': 'Ethernet', 'type': 'ethernet', 'has_gateway': True}]
        configs = {'Ethernet': {'adapter': 'Ethernet', 'mode': 'static', 'ips': ['1.1.1.1']}}
        app._apply_refresh(adapters, configs, 'monitor')

        app._start_repair.assert_called_once_with(['Ethernet'], auto=True)

    def test_manual_refresh_does_not_trigger_auto_repair(self):
        self.get_settings.stop()
        self.get_settings = patch('main.core.get_settings', return_value={
            'auto_monitor': True,
            'monitor_interval': 5,
            'auto_repair': True,
            'flush_on_repair': True,
        })
        self.get_settings.start()
        self.addCleanup(self.get_settings.stop)

        app = self._create_app()
        app._start_repair = Mock()

        adapters = [{'name': 'Ethernet', 'type': 'ethernet', 'has_gateway': True}]
        configs = {'Ethernet': {'adapter': 'Ethernet', 'mode': 'static', 'ips': ['1.1.1.1']}}
        app._apply_refresh(adapters, configs, 'manual')

        app._start_repair.assert_not_called()


if __name__ == '__main__':
    unittest.main()
