# Test case
import re
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
        """ON 状态（suyi_q_on.png）：应判定为开启 → 不触发 Q
        判定规则：两个都匹配到时比置信度，仅 ON 匹配到也视为开启"""
        self.set_image('tests/images/suyi_q_on.png')
        on_result = self.task.find_one('suyi_q_on')
        off_result = self.task.find_one('suyi_q_off')
        self.logger.info(f'ON image: on={on_result}, off={off_result}')
        self.assertIsNotNone(on_result, "ON template should match on ON image")
        if off_result is not None:
            # 两个都匹配到了 → ON 置信度必须更高
            self.assertGreater(on_result.confidence, off_result.confidence,
                               f"ON conf ({on_result.confidence:.3f}) should be > OFF conf ({off_result.confidence:.3f})")

    def test_feature11(self):
        """OFF 状态（suyi_q_off.png）：应判定为关闭 → 触发 Q
        判定规则：两个都匹配到时比置信度，仅 OFF 匹配到也视为关闭"""
        self.set_image('tests/images/suyi_q_off.png')
        on_result = self.task.find_one('suyi_q_on')
        off_result = self.task.find_one('suyi_q_off')
        self.logger.info(f'OFF image: on={on_result}, off={off_result}')
        self.assertIsNotNone(off_result, "OFF template should match on OFF image")
        if on_result is not None:
            # 两个都匹配到了 → OFF 置信度必须更高
            self.assertGreater(off_result.confidence, on_result.confidence,
                               f"OFF conf ({off_result.confidence:.3f}) should be > ON conf ({on_result.confidence:.3f})")

    def test_find_letter_btn(self):
        """密函确认按钮：find_letter_btn 应能匹配到"""
        self.set_image('tests/images/find_letter_btn.png')
        result = self.task.find_letter_btn()
        self.assertIsNotNone(result, "letter_btn should be found")
        self.logger.info(f'find_letter_btn: {result}')

if __name__ == '__main__':
    unittest.main()
