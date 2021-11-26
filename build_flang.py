#!/usr/bin/env python

import argparse
import settings
import platform
import os
import shutil
import sys
import subprocess
from pathlib import Path, PurePosixPath
import multiprocessing

def default_toolchain():
    system = platform.uname()[0]
    machine = platform.uname()[4]
    toolchain = os.path.join(settings.THIS_DIR,
                             'cmake',
                             'toolchain_%s_%s.cmake' % (system.lower(), machine.lower()))
    return toolchain if os.path.isfile(toolchain) else None

def get_arguments():
    parser = argparse.ArgumentParser(description="Help configure and build Flang")

    buildopt = parser.add_argument_group('general build options')
    buildopt.add_argument('--builddir', metavar='DIR', default=os.path.join(settings.FLANG_DIR, 'build'),
                          help='specify build directory (default: %(default)s)')
    buildopt.add_argument('--clean', action='store_true', default=False,
                          help='clean build')
    buildopt.add_argument('--build-type', metavar='TYPE', default='Release',
                          help='set build type (default: %(default)s)')
    buildopt.add_argument('--debug', dest='build_type', action='store_const', const='Debug', default=argparse.SUPPRESS,
                          help='debug build (alias for --build-type %(const)s)')
    buildopt.add_argument('--cmake-param', metavar='OPT', action='append', default=[],
                          help='add custom argument to CMake')
    buildopt.add_argument('--install-prefix', metavar='PATH', nargs='?', default=None, const=False,
                          help='install after build, also specify LLVM dir')
    buildopt.add_argument('--toolchain', metavar='FILE', default=default_toolchain(),
                          help='specify toolchain file (default: %(default)s)')
    buildopt.add_argument('--llvm-root', dest='install_prefix', metavar='PATH', default=None,
                          help='alias for install')
    buildopt.add_argument('--target', metavar='ARCH', choices=['X86', 'AArch64', 'PowerPC'], default='X86',
                          help='Control which targets are enabled (%(choices)s)')
    buildopt.add_argument('-j', '--jobs', metavar='N', type=int, default=1,
                          help='number of parallel build jobs (default: %(default)s)')
    #multiprocessing.cpu_count() +
    arguments = parser.parse_args()
    return arguments

def generate_buildoptions(arguments):
    install_root = Path(arguments.install_prefix)
    
    base_cmake_args = [
      '-DCMAKE_INSTALL_PREFIX=%s' % install_root.as_posix(),
      '-DCMAKE_BUILD_TYPE=%s' % arguments.build_type,
      '-DCMAKE_TOOLCHAIN_FILE=%s' % arguments.toolchain
    ]
    # On Windows on ARM we have to use NMake, Ninja is not available.
    if sys.platform == 'win32' and platform.uname()[4].lower() == 'arm64':
      a = '-G%s' % 'NMake Makefiles'
      print(a)
      base_cmake_args.append('-G %s' % '\"NMake Makefiles\"')
    else:
      base_cmake_args.append('-G%s' % 'Ninja' if sys.platform == 'win32' else 'Make')
    if arguments.cmake_param:
        base_cmake_args.extend(arguments.cmake_param)
    return base_cmake_args

def configure_builddir(arguments, dir):
    print(arguments.builddir)
    print(dir)
    if not os.path.isabs(arguments.builddir):
        arguments.builddir = os.path.join(dir, arguments.builddir)

    if arguments.clean and os.path.exists(arguments.builddir):
        shutil.rmtree(arguments.builddir)

    if not os.path.exists(arguments.builddir):
        os.makedirs(arguments.builddir)

def configure_libpgmath(arguments):
    configure_builddir(arguments, settings.LIBPGMATH_DIR)

    build_options = generate_buildoptions(arguments)

    cmake_cmd = ['cmake', '-B' + arguments.builddir, '-H' + settings.LIBPGMATH_DIR]
    
    cmake_cmd.extend(build_options)
    return subprocess.call(cmake_cmd)

def configure_flang(arguments):
    configure_builddir(arguments, settings.FLANG_DIR)

    build_options = generate_buildoptions(arguments)
    install_root = Path(arguments.install_prefix)
    additional_options = [
      '-DCMAKE_Fortran_COMPILER=%s' % (install_root / 'bin' /'flang.exe').as_posix(),
      '-DCMAKE_Fortran_COMPILER_ID=Flang',
      '-DFLANG_INCLUDE_DOCS=ON',
      '-DFLANG_LLVM_EXTENSIONS=ON',
      '-DLLVM_TARGETS_TO_BUILD=%s' % arguments.target,
      '-DWITH_WERROR=ON'
    ]
    build_options.extend(additional_options)
    cmake_cmd = ['cmake', '-B' + arguments.builddir, '-H' + settings.FLANG_DIR]
    
    cmake_cmd.extend(build_options)
    return subprocess.call(cmake_cmd)

def build_project(arguments):
    build_cmd = ['cmake', '--build', arguments.builddir, '--config', arguments.build_type, '--parallel', str(arguments.jobs)]
    proc = subprocess.Popen(build_cmd)
    proc.wait()

    return proc.returncode

def install_project(arguments):
    install_cmd = ['cmake', '--build', arguments.builddir, '--config', arguments.build_type, '--target', 'install']
    return subprocess.call(install_cmd)

def check_result(ret):
    print('=' * 30)
    if ret:
        print('Build failed with exit code: %s' % (ret))
    else:
        print('Build succeeded!')
    print('=' * 30)

def main():
    arguments = get_arguments()

    print("Building libpgmath...")
    ret = configure_libpgmath(arguments)
    if not ret:
        ret = build_project(arguments)

    if not ret:
        ret = install_project(arguments)

    check_result(ret)
    if ret:
        sys.exit(ret)

    print("Building flang...")
    ret = configure_flang(arguments)
    if not ret:
        ret = build_project(arguments)

    if not ret:
        ret = install_project(arguments)

    check_result(ret)
    sys.exit(ret)

if __name__ == "__main__":
    main()
