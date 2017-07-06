import errno
import signal
import sys
import time
from subprocess import Popen, PIPE

from IPython.core import magic_arguments
from IPython.core.magic import cell_magic, magics_class, Magics
from IPython.display import display
from IPython.utils import py3compat

# noinspection PyPackageRequirements
from PIL import Image

# Inspired from https://github.com/takluyver/bash_kernel/blob/master/bash_kernel/images.py
_PREFIX = "__bash_with_display__"

image_setup_cmd = """
display () {
    echo "%s $1"
}
""" % _PREFIX


def extract_display_filenames(out):
    rest = []
    filenames = []

    for line in out.split("\n"):
        if line.startswith(_PREFIX):
            filenames.extend(line.strip().split(" ")[1:])

        else:
            rest.append(line)

    return filenames, "\n".join(rest)


@magics_class
class BashWithDisplay(Magics):
    def __init__(self, shell=None):
        super(BashWithDisplay, self).__init__(shell=shell)

    @magic_arguments.magic_arguments()
    @cell_magic("bash_with_display")
    def shebang(self, _, cell):
        """Run a cell via a shell command

        The `%%script` line is like the #! line of script,
        specifying a program (bash, perl, ruby, etc.) with which to run.

        The rest of the cell is run by that program.

        Examples
        --------
        ::

            In [1]: %%script bash
               ...: for i in 1 2 3; do
               ...:   echo $i
               ...: done
            1
            2
            3
        """
        try:
            p = Popen("bash", stdout=PIPE, stderr=PIPE, stdin=PIPE)
        except OSError as e:
            if e.errno == errno.ENOENT:
                print("Couldn't find program: bash")
                return
            else:
                raise

        # Inject built in commands
        cell = '\n'.join([image_setup_cmd, cell])

        if not cell.endswith('\n'):
            cell += '\n'
        cell = cell.encode('utf8', 'replace')

        try:
            out, err = p.communicate(cell)
        except KeyboardInterrupt:
            try:
                p.send_signal(signal.SIGINT)
                time.sleep(0.1)
                if p.poll() is not None:
                    print("Process is interrupted.")
                    return
                p.terminate()
                time.sleep(0.1)
                if p.poll() is not None:
                    print("Process is terminated.")
                    return
                p.kill()
                print("Process is killed.")
            except OSError:
                pass
            except Exception as e:
                print("Error while terminating subprocess (pid=%i): %s" % (p.pid, e))
            return

        out = py3compat.bytes_to_str(out)
        err = py3compat.bytes_to_str(err)

        filenames, out = extract_display_filenames(out)
        for filename in filenames:
            # noinspection PyBroadException
            image = Image.open(filename)
            display(image)

        sys.stdout.write(out)
        sys.stdout.flush()
        sys.stderr.write(err)
        sys.stderr.flush()


def load_ipython_extension(ipython):
    ipython.register_magics(BashWithDisplay)


def unload_ipython_extension(_):
    pass
