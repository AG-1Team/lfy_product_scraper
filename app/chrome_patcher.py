# patch_driver.py
from undetected_chromedriver import Patcher

assert Patcher(executable_path='/usr/local/bin/chromedriver').patch()
