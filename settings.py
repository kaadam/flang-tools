import os

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
FLANG_DIR = os.path.abspath(os.path.join(THIS_DIR, '..'))
TOOLCHAIN_DIR = os.path.join(THIS_DIR, 'cmake')
LIBPGMATH_DIR = os.path.join(FLANG_DIR, 'runtime', 'libpgmath')