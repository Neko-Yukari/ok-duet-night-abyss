# Test case
import unittest

from src.config import config
from ok.test.TaskTestCase import TaskTestCase

from src.tasks.CommissionsTask import CommissionsTask


class TestMissonInterface(TaskTestCase):
    task_class = CommissionsTask

    config = config

    def test_feature1(self):
        self.set_image('tests/images/iface_esc.png')
        feature = self.task.find_esc_menu()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature2(self):
        self.set_image('tests/images/iface_ltr_drop.png')
        feature = self.task.find_letter_reward_btn()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature3(self):
        self.set_image('tests/images/iface_ltr.png')
        feature = self.task.find_letter_btn()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature4(self):
        self.set_image('tests/images/iface_start.png')
        feature = self.task.find_bottom_start_btn()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature5(self):
        self.set_image('tests/images/iface_cont.png')
        feature = self.task.find_ingame_continue_btn()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature6(self):
        self.set_image('tests/images/iface_drop.png')
        feature = self.task.find_drop_item()
        self.assertIsNotNone(feature)
        self.logger.info(feature)
        
    def test_feature7(self):
        self.set_image('tests/images/iface_drop2.png')
        feature = self.task.find_drop_item()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature8(self):
        self.set_image('tests/images/iface_drop2.png')
        feature = self.task.find_drop_rate_btn()
        self.assertIsNotNone(feature)
        self.logger.info(feature)

    def test_feature9(self):
        self.set_image('tests/images/iface_drop.png')
        feature = self.task.find_drop_rate_btn()
        self.assertIsNotNone(feature)
        self.logger.info(feature)


    def test_feature10(self):
        """ON 状态（显示 0）：模板匹配应找到 q_mp（置信度 1.0 > 0.95）"""
        self.set_image('tests/images/q_mp_test.png')
        result = self.task.find_one('q_mp', threshold=0.95)
        self.assertIsNotNone(result, "Should detect q_mp when toggle is ON (showing 0)")
        self.logger.info(f'ON state: confidence={result.confidence}')

    def test_feature11(self):
        """OFF 状态（显示 6）：模板匹配不应找到 q_mp（置信度 0.846 < 0.95）"""
        self.set_image('tests/images/q_mp_off.png')
        result = self.task.find_one('q_mp', threshold=0.95)
        self.assertIsNone(result, "Should NOT detect q_mp when toggle is OFF (showing non-zero)")

if __name__ == '__main__':
    unittest.main()
