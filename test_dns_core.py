import os
import tempfile
import unittest
from unittest.mock import call, patch

import dns_core


class DnsCoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.original_backup_file = dns_core.BACKUP_FILE
        self.original_log_file = dns_core.LOG_FILE
        self.original_settings_file = dns_core.SETTINGS_FILE
        self.addCleanup(self._restore_paths)

        dns_core.BACKUP_FILE = os.path.join(self.tempdir.name, 'backups.json')
        dns_core.LOG_FILE = os.path.join(self.tempdir.name, 'log.json')
        dns_core.SETTINGS_FILE = os.path.join(self.tempdir.name, 'settings.json')

    def _restore_paths(self):
        dns_core.BACKUP_FILE = self.original_backup_file
        dns_core.LOG_FILE = self.original_log_file
        dns_core.SETTINGS_FILE = self.original_settings_file

    def test_run_raises_on_nonzero_exit_code(self):
        completed = unittest.mock.Mock(returncode=1, stdout=b'', stderr='boom'.encode('utf-8'))
        with patch('dns_core.subprocess.run', return_value=completed):
            with self.assertRaises(dns_core.CommandError) as ctx:
                dns_core.run(['netsh', 'interface', 'show', 'interface'])

        self.assertIn('boom', str(ctx.exception))

    def test_repair_dns_fails_when_verification_does_not_switch_to_dhcp(self):
        configs = [
            {'adapter': 'Ethernet', 'mode': 'static', 'ips': ['1.1.1.1']},
            {'adapter': 'Ethernet', 'mode': 'static', 'ips': ['1.1.1.1']},
        ]
        with patch('dns_core.get_dns_config', side_effect=configs), \
             patch('dns_core.run', return_value='ok'), \
             patch('dns_core._save_backup'), \
             patch('dns_core._add_log') as add_log:
            result = dns_core.repair_dns('Ethernet')

        self.assertFalse(result['success'])
        self.assertIn('校验失败', result['error'])
        self.assertFalse(add_log.call_args.args[4])

    def test_save_backup_keeps_last_ten_per_adapter_and_preserves_other_adapters(self):
        seed = [
            {'adapter': 'A', 'mode': 'static', 'ips': ['1.1.1.1'], 'ts': f'a{i}'}
            for i in range(12)
        ] + [
            {'adapter': 'B', 'mode': 'dhcp', 'ips': [], 'ts': f'b{i}'}
            for i in range(3)
        ]
        dns_core._save_json(dns_core.BACKUP_FILE, seed)

        dns_core._save_backup({'adapter': 'A', 'mode': 'dhcp', 'ips': []})
        backups = dns_core.get_backups()

        a_backups = [item for item in backups if item['adapter'] == 'A']
        b_backups = [item for item in backups if item['adapter'] == 'B']

        self.assertEqual(len(a_backups), 10)
        self.assertEqual(len(b_backups), 3)
        self.assertEqual(a_backups[0]['ts'], 'a3')
        self.assertEqual(a_backups[-1]['mode'], 'dhcp')

    def test_rollback_restores_all_static_dns_servers(self):
        backup = {
            'adapter': 'Ethernet',
            'mode': 'static',
            'ips': ['1.1.1.1', '8.8.8.8', '9.9.9.9'],
        }
        configs = [
            {'adapter': 'Ethernet', 'mode': 'dhcp', 'ips': []},
            {'adapter': 'Ethernet', 'mode': 'static', 'ips': ['1.1.1.1', '8.8.8.8', '9.9.9.9']},
        ]
        with patch('dns_core.get_dns_config', side_effect=configs), \
             patch('dns_core.run', return_value='ok') as run_cmd, \
             patch('dns_core._add_log'):
            result = dns_core.rollback(backup)

        self.assertTrue(result['success'])
        self.assertEqual(run_cmd.call_args_list, [
            call(['netsh', 'interface', 'ip', 'set', 'dns', 'Ethernet', 'static', '1.1.1.1']),
            call(['netsh', 'interface', 'ip', 'add', 'dns', 'Ethernet', '8.8.8.8', 'index=2']),
            call(['netsh', 'interface', 'ip', 'add', 'dns', 'Ethernet', '9.9.9.9', 'index=3']),
        ])

    def test_save_settings_filters_unknown_keys(self):
        dns_core.save_settings({
            'auto_monitor': True,
            'monitor_interval': 10,
            'auto_repair': True,
            'flush_on_repair': False,
            'language': 'en',
        })

        with open(dns_core.SETTINGS_FILE, 'r', encoding='utf-8') as handle:
            saved = handle.read()

        self.assertIn('"auto_monitor": true', saved)
        self.assertNotIn('language', saved)


if __name__ == '__main__':
    unittest.main()
