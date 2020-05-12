"""
Minimal BSS impl for testing the general functions in BSSCommon.py
"""

import re
from BSSCommon import BSSBase

class BSS(BSSBase):
    def get_variant(self):
        return "Testing"

    defaults = {}
    
    def create_submit_script(self, message, config, LOG):
        submit_cmds = []
        submit_cmds.append("#!/bin/bash")
        return submit_cmds
