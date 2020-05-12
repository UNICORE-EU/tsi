"""
Utility methods for checking that the TSI is working as expected.

Usage

  'export PYTHONPATH=lib; cmd | python -m lib/Validation <arg>'

Will run validation on the output from 'cmd'

where 'arg' is
 - 'qstat' (or nothing) : run qstat output conversion

"""

import sys
from BSS import BSS


def validate_qstat():
    """
    Runs stdin through parse_status_listing()
    """
    print('Converting qstat output...\n')
    qstat = sys.stdin.read()
    print(BSS().parse_status_listing(qstat))
    print('')
    print("CHECK: If you did not see output after the initial 'QSTAT' line, "
          "please check the BSS.py file!")


def main(argv=None):
    validate_qstat()


# application entry point
if __name__ == "__main__":
    main()
