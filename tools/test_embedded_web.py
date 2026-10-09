"""Verify actual C-compiled HTTP pages; C99 trigraphs must never alter JS."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class EmbeddedWebTests(unittest.TestCase):
    def test_compiled_pages_match_sources_and_js_parses(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'dump.c';binary=root/'dump'
            source.write_text('#include <stdio.h>\n#include "hamlab_web.h"\nint main(int argc,char **argv){(void)argv;fputs(argc>2?compact_a2_html:argc>1?compact_html:html,stdout);return 0;}\n')
            subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror','-Wtrigraphs','-I'+str(ROOT/'src'),str(source),'-o',str(binary)],check=True)
            for name,args in [('hamlab',[]),('compact',['compact']),('compact-a2',['compact','a2'])]:
                actual=subprocess.check_output([str(binary),*args])
                self.assertEqual(actual,(ROOT/'web'/f'{name}.html').read_bytes())
                js=actual.decode().split('<script>',1)[1].split('</script>',1)[0]
                script=root/f'{name}.js';script.write_text(js)
                if shutil.which('node'):subprocess.run(['node','--check',str(script)],check=True)
    @unittest.skipUnless(shutil.which('node'),'Node required for plot verification')
    def test_independent_curve_scales(self):
        subprocess.run(['node',str(ROOT/'tools/test_curve_plots.js')],check=True)
if __name__=='__main__':unittest.main()
