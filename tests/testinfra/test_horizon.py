# Copyright 2018 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import yaml

from pathlib import Path
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

home = Path.home()
subpath = '/testinfra/screenshots/'
screenshot_path = str(home) + subpath

with open("/etc/kolla/passwords.yml", 'r') as file:
    passwords = yaml.safe_load(file)
    admin_password = passwords.get('keystone_admin_password')


def test_horizon_screenshot(host):

    firefox_options = webdriver.FirefoxOptions()

    driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=firefox_options)

    horizon_proto = host.environment().get('HORIZON_PROTO')
    horizon_url = horizon_proto + "://192.0.2.10"

    try:
        driver.get(horizon_url)
        WebDriverWait(driver, 30).until(
            lambda driver: driver.execute_script(
                'return document.readyState') == 'complete')

        time.sleep(5)

        original_size = driver.get_window_size()
        required_width = driver.execute_script(
            'return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script(
            'return document.body.parentNode.scrollHeight') + 100
        driver.set_window_size(required_width, required_height)

        driver.find_element(By.TAG_NAME, 'body').\
            screenshot(screenshot_path + "horizon-main.png")  # nosec B108

        driver.set_window_size(
            original_size['width'], original_size['height'])

        assert 'Login' in driver.title  # nosec B101

    except TimeoutException as e:
        raise e
    finally:
        driver.quit()


def test_horizon_login(host):

    firefox_options = webdriver.FirefoxOptions()

    driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=firefox_options)

    horizon_proto = host.environment().get('HORIZON_PROTO')
    horizon_url = horizon_proto + "://192.0.2.10"
    logout_url = '/'.join((
                 horizon_url,
                 'auth',
                 'logout'))

    try:
        driver.get(logout_url)
        user_field = driver.find_element(By.ID, 'id_username')
        user_field.send_keys('admin')
        pass_field = driver.find_element(By.ID, 'id_password')
        pass_field.send_keys(admin_password)
        button = driver.find_element(By.CSS_SELECTOR, '.btn-primary')
        button.click()
        WebDriverWait(driver, 30).until(
            lambda driver: driver.execute_script(
                'return document.readyState') == 'complete')

        time.sleep(10)

        original_size = driver.get_window_size()
        required_width = driver.execute_script(
            'return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script(
            'return document.body.parentNode.scrollHeight') + 100
        driver.set_window_size(required_width, required_height)

        driver.find_element(By.TAG_NAME, 'body').\
            screenshot(screenshot_path + "horizon-logged-in.png")  # nosec B108

        driver.set_window_size(
            original_size['width'], original_size['height'])

        assert 'Overview - OpenStack Dashboard' in driver.title  # nosec B101

    except TimeoutException as e:
        raise e
    finally:
        driver.quit()
