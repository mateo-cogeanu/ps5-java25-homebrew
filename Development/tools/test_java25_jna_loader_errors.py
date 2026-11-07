#!/usr/bin/env python3
"""Exercise actual pinned JNA loader JNI paths with refused error allocation."""
from pathlib import Path
import argparse
import os
import resource
import subprocess
import tempfile

from java25_jna import ROOT, JDK, LLVM, COMMIT


def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def fixture(text):
    error = function(text, 'static inline char * LOAD_ERROR()')
    operations = '\n'.join(('void ' if name == 'close' else 'jlong ') + function(text, 'Java_com_sun_jna_Native_' + name + '(')
                           for name in ('open', 'close', 'findSymbol'))
    return r"""
#include <jni.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) x
#define A2L(x) ((jlong)(intptr_t)(x))
#define L2A(x) ((void*)(intptr_t)(x))
#include <stdint.h>
#define STRTYPE char*
#define DEFAULT_LOAD_OPTS 0
#define EUnsatisfiedLink "java/lang/UnsatisfiedLinkError"
#define EError "java/lang/Error"
static int refused, thrown;
static const char *error_text;
static const char *dlerror(void) { return error_text; }
static __attribute__((noinline)) void *error_malloc(size_t size) { return refused ? NULL : malloc(size); }
#define malloc error_malloc
""" + error + r"""
#undef malloc
static char *newCString(JNIEnv *env, jstring value) { return strdup("missing_native"); }
#define NAME2CSTR(env, value) newCString(env, value)
#define LOAD_LIBRARY(name, flags) NULL
#define FREE_LIBRARY(handle) -1
#define FIND_ENTRY(handle, name) NULL
static void throwByName(JNIEnv *env, const char *type, const char *message) {
    assert(message != NULL);
    if (refused) {
        assert(strstr(message, "allocation refused") != NULL);
    } else if (error_text) {
        assert(strcmp(message, error_text) == 0);
    } else {
        assert(strstr(message, "without loader error text") != NULL);
    }
    assert(strcmp(type, EUnsatisfiedLink) == 0 || strcmp(type, EError) == 0);
    thrown++;
}
""" + operations + r"""
int main(int argc, char **argv) {
    int all = argc > 1;
    for (int missing = 0; missing <= all; missing++) {
        error_text = missing ? NULL : "resident library is unavailable";
        for (refused = 0; refused <= 1; refused++) {
            thrown = 0;
            assert(Java_com_sun_jna_Native_open(NULL, NULL, (jstring)1, -1) == 0);
            Java_com_sun_jna_Native_close(NULL, NULL, 1);
            assert(Java_com_sun_jna_Native_findSymbol(NULL, NULL, 1, (jstring)1) == 0);
            assert(thrown == 3);
        }
    }
    puts("PASS real JNA open/close/findSymbol: loader error, missing text, allocation refusal");
    return 0;
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.tools/jna-5.19.1')
    args = parser.parse_args()
    original = subprocess.check_output(
        ['git', '-C', str(args.source), 'show', COMMIT + ':native/dispatch.c'], text=True)
    patch = ROOT / 'java25/patches/jna/0001-checked-loader-errors.patch'
    with tempfile.TemporaryDirectory(prefix='jna-errors-') as directory:
        work = Path(directory)
        (work / 'native').mkdir()
        source = work / 'native/dispatch.c'
        source.write_text(original)
        subprocess.run(['patch', '-p1', '--batch', '-i', str(patch)], cwd=work, check=True)
        for name, text in [('historical', original), ('checked', source.read_text())]:
            c_file, executable = work / (name + '.c'), work / name
            c_file.write_text(fixture(text))
            subprocess.run([str(LLVM / 'clang'), '-O1', '-g', '-fno-builtin', '-fsanitize=address,undefined',
                            '-I' + str(JDK / 'include'), '-I' + str(JDK / 'include/darwin'),
                            str(c_file), '-o', str(executable)], check=True)
            def disable_core():
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            result = subprocess.run([str(executable), *(['all'] if name == 'checked' else [])],
                                    capture_output=True, text=True, timeout=15,
                                    env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'},
                                    preexec_fn=disable_core)
            if name == 'historical':
                assert result.returncode != 0 and 'AddressSanitizer' in result.stderr, result.stderr
                print('PASS historical allocation-refusal reproducer faults under sanitizer')
            else:
                assert result.returncode == 0, result.stderr
                print(result.stdout.strip())


if __name__ == '__main__':
    main()
