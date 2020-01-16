import os
from typing import List
from .base_target import BuildTarget, SingleBuildTarget
from .. import os_utils

class RonnBuildTarget(BuildTarget):
    BT_LABEL = 'RONN'
    def __init__(self, markdown_filename, section:int=1, dependencies: List[str]=[], ronn_executable: str=None):
        self.markdown_filename: str = markdown_filename
        self.section: int = section
        self.dependencies: List[str] = dependencies
        self.ronn_executable: str = ronn_executable or os_utils.which('ronn')

        self.parent_dir: str = os.path.dirname(self.markdown_filename)
        basename, _ = os.path.splitext(os.path.basename(self.markdown_filename))
        self.roff_filename: str = os.path.join(self.parent_dir, f'{basename}')
        self.html_filename: str = os.path.join(self.parent_dir, f'{basename}.html')
        super().__init__(targets=[self.roff_filename, self.html_filename], files=[markdown_filename], dependencies=dependencies)

    def build(self):
        os_utils.cmd([self.ronn_executable, self.markdown_filename], echo=self.should_echo_commands(), show_output=False)
